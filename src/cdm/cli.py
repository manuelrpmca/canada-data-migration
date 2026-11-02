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
    p_chart = sub.add_parser("chart", help="SVG chart of the monthly mart (for the README)")
    p_chart.add_argument(
        "--out", type=Path, default=None, help="output file (default: docs/img/indicators.svg)"
    )
    sub.add_parser("verify", help="check every series identifier against the live APIs")
    p_oracle = sub.add_parser("oracle", help="the Oracle system of record (M4): cdm oracle --help")
    osub = p_oracle.add_subparsers(dest="oracle_command", required=True)
    osub.add_parser("up", help="start Oracle in Docker, create passwords in .env, run setup")
    p_down = osub.add_parser("down", help="stop the Oracle container (data is kept)")
    p_down.add_argument(
        "--delete-data", action="store_true", help="also delete the database (cannot be undone)"
    )
    osub.add_parser("setup", help="create or update accounts, tables, views and the package")
    osub.add_parser("load", help="load every landed file in data/raw not loaded yet")
    osub.add_parser("status", help="periods, revisions and files per series (read-only user)")
    p_osql = osub.add_parser("sql", help="run one SQL statement as the read-only migration user")
    p_osql.add_argument("statement")
    osub.add_parser("compare", help="row counts and totals: Oracle current values vs DuckDB")
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
        "chart": lambda: _chart(db_path, args.out),
        "oracle": lambda: _oracle(db_path, args),
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


def _chart(db_path: Path, out: Path | None) -> int:
    if _missing_warehouse(db_path):
        return 1
    from cdm import chart

    out = out or settings.project_root() / "docs" / "img" / "indicators.svg"
    con = warehouse.connect(db_path)
    try:
        path = chart.write(con, out, datetime.now(UTC).date())
    finally:
        con.close()
    print(f"Chart written to {path}")
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


def _oracle(db_path: Path, args: argparse.Namespace) -> int:
    from cdm import container
    from cdm.load import oracle

    command = args.oracle_command
    try:
        if command == "up":
            filled = oracle.ensure_passwords(oracle.env_file())
            if filled:
                print(
                    f"Created random passwords in .env (git-ignored): {', '.join(filled)}",
                    flush=True,
                )
            print("Starting Oracle. The first time, Docker downloads about 1.3 GB.", flush=True)
            if container.up() != 0:
                return 1
            return _oracle_setup(oracle.load_settings())
        if command == "down":
            return container.down(args.delete_data)
        cfg = oracle.load_settings()
        if command == "setup":
            return _oracle_setup(cfg)
        if command == "load":
            return _oracle_load(cfg)
        if command == "status":
            return _oracle_status(cfg)
        if command == "sql":
            with oracle.connect_migration(cfg) as con:
                columns, rows = oracle.query(con, args.statement)
            _print_rows(columns, rows)
            return 0
        if command == "compare":
            return _oracle_compare(cfg, db_path)
    except (container.DockerError, oracle.OracleConfigError, oracle.SetupError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except oracle.oracledb.Error as exc:
        print(f"Oracle error: {str(exc).splitlines()[0]}", file=sys.stderr)
        if "DPY-6005" in str(exc) or "DPY-4011" in str(exc):
            print("Is Oracle running? Start it with `uv run cdm oracle up`.", file=sys.stderr)
        return 1
    return 2


def _oracle_setup(cfg) -> int:
    from cdm.load import oracle

    for name, count in oracle.setup(cfg):
        print(f"setup {name:<24} {count:>3} statements")
    print(f"Oracle ready: owner {cfg.owner}, loader {cfg.loader}, read-only {cfg.migration}.")
    return 0


def _oracle_load(cfg) -> int:
    from cdm.load import oracle

    with oracle.connect_loader(cfg) as con:
        results = oracle.load(con, cfg.owner, settings.load_series(), settings.data_dir())
    header = ("series", "files", "loaded", "already", "ins", "rev", "same", "skip")
    print("{:<22} {:>6} {:>6} {:>7} {:>6} {:>6} {:>6} {:>6}".format(*header))
    for r in results:
        print(
            f"{r.series_key:<22} {r.files:>6} {r.loaded:>6} {r.already:>7} {r.inserted:>6} "
            f"{r.revised:>6} {r.unchanged:>6} {r.skipped:>6}"
            + (f"  FAILED {r.message}" if r.failed else "")
        )
    if not any(r.files for r in results):
        print(f"No landed files in {settings.data_dir() / 'raw'}. Run `uv run cdm ingest` first.")
    return 1 if any(r.failed for r in results) else 0


def _oracle_status(cfg) -> int:
    from cdm.load import oracle

    with oracle.connect_migration(cfg) as con:
        rows = oracle.status(con)
    header = ("series", "periods", "revised", "files", "first", "last", "last load (UTC)")
    print("{:<22} {:>7} {:>7} {:>6} {:<10} {:<10} {}".format(*header))
    for key, current, revised, files, first, last, loaded in rows:
        when = f"{loaded:%Y-%m-%d %H:%M}" if loaded else "never"
        print(
            f"{key:<22} {current:>7} {revised:>7} {files:>6} "
            f"{_day(first):<10} {_day(last):<10} {when}"
        )
    return 0


def _day(value) -> str:
    return f"{value:%Y-%m-%d}" if value else "-"


def _oracle_compare(cfg, db_path: Path) -> int:
    from cdm.load import oracle

    if _missing_warehouse(db_path):
        return 1
    with oracle.connect_migration(cfg) as con:
        ora = oracle.profile_oracle(con)
    duck_con = warehouse.connect(db_path)
    try:
        duck = oracle.profile_duckdb(duck_con)
    finally:
        duck_con.close()
    print(
        f"{'series':<22} {'oracle':>7} {'duckdb':>7} {'oracle sum':>14} {'duckdb sum':>14} result"
    )
    ok = True
    for key, o, d, result in oracle.compare(ora, duck):
        ok = ok and result == "match"
        print(
            f"{key:<22} {o.rows if o else '-':>7} {d.rows if d else '-':>7} "
            f"{f'{o.total:.4f}' if o else '-':>14} {f'{d.total:.4f}' if d else '-':>14} {result}"
        )
    return 0 if ok else 1


def _print_rows(columns: list[str] | None, rows: list[tuple]) -> None:
    if columns is None:
        print("OK")
        return
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join("" if v is None else str(v) for v in row))


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
