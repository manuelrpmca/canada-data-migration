"""Command line entry point: `uv run cdm <command>`. Works the same on Windows, macOS and Linux."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from cdm import pipeline, settings, transform
from cdm.http import make_client
from cdm.load import duckdb as warehouse
from cdm.sources import statcan, valet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cdm", description=__doc__)
    parser.add_argument("--db", type=Path, help="DuckDB file (default: data/warehouse.duckdb)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="fetch new data from the APIs and upsert it")
    p_ingest.add_argument("--series", action="append", help="series key (repeatable); default all")
    p_run = sub.add_parser("run", help="ingest, then dbt build (the full pipeline)")
    p_run.add_argument("--skip-ingest", action="store_true", help="only run dbt build")
    p_dbt = sub.add_parser(
        "dbt", help="run any dbt command from any folder, e.g. cdm dbt docs serve"
    )
    p_dbt.add_argument("dbt_args", nargs=argparse.REMAINDER, help="dbt arguments")
    sub.add_parser("status", help="rows and date range per series, and the last run")
    p_sql = sub.add_parser("sql", help="run one SQL statement against the warehouse")
    p_sql.add_argument("statement")
    sub.add_parser("verify", help="check every series identifier against the live APIs")
    p_find = sub.add_parser("find-vector", help="StatCan: vector ID for a table coordinate")
    p_find.add_argument("product_id", type=int)
    p_find.add_argument(
        "coordinate", help='member IDs per dimension, e.g. "14.2" (padded to 10 positions)'
    )

    argv, dbt_args = _split_dbt_args(sys.argv[1:] if argv is None else list(argv))
    args = parser.parse_args(argv)
    if args.command == "dbt":
        args.dbt_args = dbt_args
    db_path = args.db or settings.default_db_path()
    commands = {
        "ingest": lambda: _ingest(db_path, args.series),
        "run": lambda: _run(db_path, args.skip_ingest),
        "dbt": lambda: _dbt(db_path, args.dbt_args),
        "status": lambda: _status(db_path),
        "sql": lambda: _sql(db_path, args.statement),
        "verify": _verify,
        "find-vector": lambda: _find_vector(args.product_id, args.coordinate),
    }
    return commands[args.command]()


def _split_dbt_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Everything after the `dbt` command goes to dbt untouched. argparse alone would reject
    options such as `cdm dbt --version`, because REMAINDER does not start with an option."""
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--db":
            i += 2
        elif token.startswith("--db="):
            i += 1
        elif token == "dbt":
            return argv[: i + 1], argv[i + 1 :]
        else:
            break
    return argv, []


def _ingest(db_path: Path, only: list[str] | None) -> int:
    series = settings.load_series()
    con = warehouse.connect(db_path)
    warehouse.sync_series(con, series, datetime.now(UTC).replace(tzinfo=None))
    con.close()
    if only:
        unknown = set(only) - {s.key for s in series}
        if unknown:
            print(f"Unknown series: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        series = [s for s in series if s.key in only]
    con = warehouse.connect(db_path)
    with make_client() as client:
        results = pipeline.ingest(series, con, client, settings.data_dir())
    con.close()
    header = ("series", "status", "from", "recv", "ins", "upd", "same")
    print("{:<22} {:<8} {:<10} {:>6} {:>6} {:>6} {:>6}".format(*header))
    for r in results:
        start = r.request_start.isoformat() if r.request_start else "-"
        print(
            f"{r.series_key:<22} {r.status:<8} {start:<10} "
            f"{r.received:>6} {r.inserted:>6} {r.updated:>6} {r.unchanged:>6}"
            + (f"  {r.message}" if r.message else "")
        )
    return 1 if any(r.status == "failed" for r in results) else 0


def _run(db_path: Path, skip_ingest: bool) -> int:
    if not skip_ingest:
        code = _ingest(db_path, None)
        if code != 0:
            print("Ingest reported a failure; dbt build still runs on the data already loaded.")
        print()
    else:
        code = 0
    if _missing_warehouse(db_path):
        return 1
    ok = transform.build(db_path)
    return 0 if ok and code == 0 else 1


def _missing_warehouse(db_path: Path) -> bool:
    """True (after printing what to do) when the DuckDB file does not exist yet."""
    if db_path.exists():
        return False
    print(
        f"No warehouse at {db_path}.\n"
        "Create it with `uv run cdm run` (downloads the data, then builds the dbt models).",
        file=sys.stderr,
    )
    return True


def _dbt(db_path: Path, dbt_args: list[str]) -> int:
    # dbt-duckdb would silently create an empty warehouse file; say what to run instead.
    needs_warehouse = dbt_args and dbt_args[0] not in ("--help", "-h", "--version")
    if needs_warehouse and _missing_warehouse(db_path):
        return 1
    return 0 if transform.run(db_path, dbt_args) else 1


def _sql(db_path: Path, statement: str) -> int:
    if _missing_warehouse(db_path):
        return 1
    con = warehouse.connect(db_path)
    try:
        cursor = con.execute(statement)
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            print(" | ".join(columns))
            for row in cursor.fetchall():
                print(" | ".join("" if v is None else str(v) for v in row))
        else:
            print("OK")
    finally:
        con.close()
    return 0


def _status(db_path: Path) -> int:
    if _missing_warehouse(db_path):
        return 1
    con = warehouse.connect(db_path)
    rows = warehouse.status(con)
    con.close()
    print(f"{'series':<22} {'rows':>6} {'first':<10} {'last':<10} last run")
    for key, n, first, last, run_status, ins, upd, same, finished in rows:
        print(
            f"{key:<22} {n:>6} {first} {last} "
            f"{run_status} (+{ins} ~{upd} ={same}) at {finished:%Y-%m-%d %H:%M} UTC"
        )
    return 0


def _verify() -> int:
    ok = True
    with make_client() as client:
        for s in settings.load_series():
            print(f"\n== {s.key} ({s.source}) ==")
            try:
                if s.source == "valet":
                    print(json.dumps(valet.describe_series(client, s.series_id), indent=2)[:800])
                elif s.series_id:
                    print(json.dumps(statcan.describe_vector(client, s.series_id), indent=2)[:800])
                else:
                    ok = False
                    cube = statcan.describe_cube(client, s.product_id)
                    print("No vector ID yet. Pick members below, then run cdm find-vector.")
                    print(json.dumps(_summarize_cube(cube), indent=2))
            except Exception as exc:
                ok = False
                print(f"FAILED: {type(exc).__name__}: {exc}")
    return 0 if ok else 1


def _summarize_cube(cube: list) -> dict:
    obj = cube[0].get("object", {})
    return {
        "title": obj.get("cubeTitleEn"),
        "dimensions": [
            {
                "position": d.get("dimensionPositionId"),
                "name": d.get("dimensionNameEn"),
                "members": [
                    f"{m.get('memberId')}: {m.get('memberNameEn')}" for m in d.get("member", [])
                ][:40],
            }
            for d in obj.get("dimension", [])
        ],
    }


def _find_vector(product_id: int, coordinate: str) -> int:
    with make_client() as client:
        print(json.dumps(statcan.find_vector(client, product_id, coordinate), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
