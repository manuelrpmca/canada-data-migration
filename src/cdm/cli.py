"""Command line entry point: `uv run cdm <command>`. Works the same on Windows, macOS and Linux."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cdm import pipeline, settings
from cdm.http import make_client
from cdm.load import duckdb as warehouse
from cdm.sources import statcan, valet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cdm", description=__doc__)
    parser.add_argument("--db", type=Path, help="DuckDB file (default: data/warehouse.duckdb)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="fetch new data from the APIs and upsert it")
    p_ingest.add_argument("--series", action="append", help="series key (repeatable); default all")
    sub.add_parser("status", help="rows and date range per series, and the last run")
    sub.add_parser("verify", help="check every series identifier against the live APIs")
    p_find = sub.add_parser("find-vector", help="StatCan: vector ID for a table coordinate")
    p_find.add_argument("product_id", type=int)
    p_find.add_argument("coordinate", help='e.g. "1.2.0.0.0.0.0.0.0.0"')

    args = parser.parse_args(argv)
    db_path = args.db or settings.default_db_path()
    commands = {
        "ingest": lambda: _ingest(db_path, args.series),
        "status": lambda: _status(db_path),
        "verify": _verify,
        "find-vector": lambda: _find_vector(args.product_id, args.coordinate),
    }
    return commands[args.command]()


def _ingest(db_path: Path, only: list[str] | None) -> int:
    series = settings.load_series()
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


def _status(db_path: Path) -> int:
    if not db_path.exists():
        print(f"No warehouse at {db_path}. Run `uv run cdm ingest` first.")
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
