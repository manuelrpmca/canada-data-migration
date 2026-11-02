"""Oracle loader: the governed system of record (ADR 0009).

Python only moves bytes: it sends each landed API response, unchanged, to the PL/SQL package
`cdm_load`, which parses it and keeps the effective-dated history. The SQL that builds the
schema lives in oracle/ (ddl/ and plsql/) and runs through `setup`.

Connections use python-oracledb in thin mode: no Oracle client install, on Windows too.
Accounts (prefix CDM by default):
  SYSTEM               runs setup (accounts, then the owner's objects through a proxy connection)
  <prefix>_LOADER      runs the load package, nothing else
  <prefix>_MIGRATION   reads, nothing else (status, sql and compare connect as this account)
"""

from __future__ import annotations

import hashlib
import os
import secrets
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import oracledb

from cdm import settings
from cdm.settings import Series

DEFAULT_DSN = "localhost:1521/FREEPDB1"
PASSWORD_KEYS = ("ORACLE_PASSWORD", "ORACLE_LOADER_PASSWORD", "ORACLE_MIGRATION_PASSWORD")

# Scripts of the owner schema, in order. 01_accounts.sql runs first, as SYSTEM.
OWNER_SCRIPTS = (
    "ddl/02_tables.sql",
    "plsql/cdm_load.pks",
    "plsql/cdm_load.pkb",
    "ddl/03_views.sql",
    "ddl/04_grants.sql",
)


@dataclass(frozen=True)
class OracleSettings:
    dsn: str
    system_password: str
    loader_password: str
    migration_password: str
    prefix: str = "CDM"

    @property
    def owner(self) -> str:
        return f"{self.prefix}_OWNER"

    @property
    def loader(self) -> str:
        return f"{self.prefix}_LOADER"

    @property
    def migration(self) -> str:
        return f"{self.prefix}_MIGRATION"


class OracleConfigError(RuntimeError):
    """Settings are missing; the message says what to run."""


class SetupError(RuntimeError):
    """A setup statement failed; the message names the script and the statement."""


# --- settings and the .env file -------------------------------------------------------------


def env_file() -> Path:
    return settings.project_root() / ".env"


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=value lines; blank lines and # comments are ignored."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def new_password(length: int = 24) -> str:
    """Letters and digits, starting with a letter: valid for Oracle and the container image."""
    alphabet = string.ascii_letters + string.digits
    return secrets.choice(string.ascii_letters) + "".join(
        secrets.choice(alphabet) for _ in range(length - 1)
    )


def ensure_passwords(path: Path) -> list[str]:
    """Give every Oracle password key in `path` (the git-ignored .env) a random value if it has
    none. Lines already there are kept. Returns the keys that were filled in."""
    values = read_env_file(path)
    missing = [k for k in PASSWORD_KEYS if not values.get(k) and not os.environ.get(k)]
    if not missing:
        return []
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    kept = [ln for ln in lines if ln.partition("=")[0].strip() not in missing]
    if not lines:
        kept.append("# Local secrets. Git-ignored; never commit. See .env.example.")
    kept += [f"{k}={new_password()}" for k in missing]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return missing


def load_settings(prefix: str = "CDM") -> OracleSettings:
    """Environment variables first, then the .env file at the repository root."""
    file_values = read_env_file(env_file())

    def get(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key) or file_values.get(key) or default

    missing = [k for k in PASSWORD_KEYS if not get(k)]
    if missing:
        raise OracleConfigError(
            f"Missing {', '.join(missing)}. Run `uv run cdm oracle up`: it creates them in .env."
        )
    return OracleSettings(
        dsn=get("ORACLE_DSN", DEFAULT_DSN),
        system_password=get("ORACLE_PASSWORD"),
        loader_password=get("ORACLE_LOADER_PASSWORD"),
        migration_password=get("ORACLE_MIGRATION_PASSWORD"),
        prefix=prefix,
    )


# --- connections ----------------------------------------------------------------------------


def connect_system(cfg: OracleSettings, proxy_to: str | None = None) -> oracledb.Connection:
    user = f"system[{proxy_to}]" if proxy_to else "system"
    return oracledb.connect(user=user, password=cfg.system_password, dsn=cfg.dsn)


def connect_loader(cfg: OracleSettings) -> oracledb.Connection:
    return oracledb.connect(user=cfg.loader, password=cfg.loader_password, dsn=cfg.dsn)


def connect_migration(cfg: OracleSettings) -> oracledb.Connection:
    """Read-only account. The session's default schema is the owner, so queries can say
    `observation_current` instead of `cdm_owner.observation_current`."""
    con = oracledb.connect(user=cfg.migration, password=cfg.migration_password, dsn=cfg.dsn)
    with con.cursor() as cur:
        cur.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {cfg.owner}")
    return con


# --- setup ----------------------------------------------------------------------------------


def oracle_dir() -> Path:
    return settings.project_root() / "oracle"


def split_script(text: str) -> list[str]:
    """Statements are separated by a line holding only "/" (SQL*Plus style). Chunks that hold
    only comments are dropped."""
    statements, current = [], []
    for line in text.splitlines():
        if line.strip() == "/":
            statements.append("\n".join(current))
            current = []
        else:
            current.append(line)
    statements.append("\n".join(current))
    return [s.strip() for s in statements if _has_code(s)]


def _has_code(chunk: str) -> bool:
    return any(ln.strip() and not ln.strip().startswith("--") for ln in chunk.splitlines())


def render(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace("{" + key + "}", value)
    return text


def run_script(con: oracledb.Connection, path: Path, replacements: dict[str, str]) -> int:
    """Run every statement of a script; raise if a PL/SQL unit compiles with errors."""
    statements = split_script(render(path.read_text(encoding="utf-8"), replacements))
    with con.cursor() as cur:
        for statement in statements:
            try:
                cur.execute(statement)
            except oracledb.DatabaseError as exc:
                first_line = next(ln for ln in statement.splitlines() if not ln.startswith("--"))
                raise SetupError(
                    f"{path.name}: {str(exc).splitlines()[0]} in statement: {first_line[:80]}"
                ) from exc
            if cur.warning:
                raise SetupError(f"{path.name}: {cur.warning}\n{_compile_errors(cur)}")
    return len(statements)


def _compile_errors(cur: oracledb.Cursor) -> str:
    cur.execute("SELECT name, type, line, position, text FROM user_errors ORDER BY name, sequence")
    return "\n".join(f"{n} {t} line {ln}:{p} {msg}" for n, t, ln, p, msg in cur.fetchall())


def setup(cfg: OracleSettings) -> list[tuple[str, int]]:
    """Create or update accounts, roles, tables, views and the package. Safe to run again:
    existing tables and data are kept; views, the package and grants are replaced."""
    replacements = {
        "p": cfg.prefix,
        "loader_password": cfg.loader_password,
        "migration_password": cfg.migration_password,
    }
    done = []
    with connect_system(cfg) as con:
        done.append(("ddl/01_accounts.sql", run_script(con, oracle_dir() / "ddl/01_accounts.sql",
                                                       replacements)))  # fmt: skip
    with connect_system(cfg, proxy_to=cfg.owner) as con:
        for name in OWNER_SCRIPTS:
            done.append((name, run_script(con, oracle_dir() / name, replacements)))
    return done


def drop_accounts(cfg: OracleSettings) -> None:
    """Drop the accounts and roles of `cfg.prefix` with all their objects (used by the tests)."""
    with connect_system(cfg) as con, con.cursor() as cur:
        for user in (cfg.loader, cfg.migration, cfg.owner):
            cur.execute(f"DROP USER IF EXISTS {user} CASCADE")
        for role in ("LOAD_ROLE", "READ_ROLE"):
            cur.execute(f"DROP ROLE IF EXISTS {cfg.prefix}_{role}")


# --- loading --------------------------------------------------------------------------------


@dataclass(frozen=True)
class LandedRun:
    source: str
    series_key: str
    run_id: str
    path: Path

    @property
    def received_at(self) -> datetime:
        """The run id starts with the UTC time the response was fetched: 20261102T150012Z-..."""
        return datetime.strptime(self.run_id[:16], "%Y%m%dT%H%M%SZ")


@dataclass
class SeriesLoad:
    series_key: str
    files: int = 0
    loaded: int = 0
    already: int = 0
    inserted: int = 0
    revised: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    message: str = ""


def landed_runs(data_dir: Path, series: Series) -> list[LandedRun]:
    """Landed files of one series, oldest first (data/raw/<source>/<series_key>/<run_id>.json)."""
    folder = data_dir / "raw" / series.source / series.key
    runs = [
        LandedRun(series.source, series.key, p.stem, p)
        for p in folder.glob("*.json")
        if _is_run_id(p.stem)
    ]
    return sorted(runs, key=lambda r: r.run_id)


def _is_run_id(stem: str) -> bool:
    try:
        datetime.strptime(stem[:16], "%Y%m%dT%H%M%SZ")
    except ValueError:
        return False
    return True


def sync_series(con: oracledb.Connection, owner: str, series: list[Series]) -> None:
    with con.cursor() as cur:
        for s in series:
            if not s.ready:
                continue
            cur.callproc(
                f"{owner}.cdm_load.sync_series",
                [s.key, s.source, s.series_id, s.product_id, s.name, s.unit, s.frequency,
                 s.start_date],
            )  # fmt: skip


def load(
    con: oracledb.Connection, owner: str, series: list[Series], data_dir: Path
) -> list[SeriesLoad]:
    """Load every landed file not loaded yet, per series in the order received. A failed file
    stops that series (later files depend on it) but not the others."""
    sync_series(con, owner, series)
    package = f"{owner}.cdm_load"
    results = []
    with con.cursor() as cur:
        for s in series:
            if not s.ready:
                continue
            result = SeriesLoad(s.key)
            for run in landed_runs(data_dir, s):
                result.files += 1
                if cur.callfunc(f"{package}.is_loaded", int, [s.key, run.run_id]):
                    result.already += 1
                    continue
                raw = run.path.read_bytes()
                out = [cur.var(int) for _ in range(5)]
                try:
                    cur.callproc(
                        f"{package}.load_file",
                        [s.key, run.run_id, run.received_at, hashlib.sha256(raw).hexdigest(),
                         raw.decode("utf-8"), *out],
                    )  # fmt: skip
                except oracledb.DatabaseError as exc:
                    result.failed += 1
                    result.message = f"{run.run_id}: {str(exc).splitlines()[0]}"
                    break
                _, inserted, revised, unchanged, skipped = (v.getvalue() for v in out)
                result.loaded += 1
                result.inserted += inserted
                result.revised += revised
                result.unchanged += unchanged
                result.skipped += skipped
            results.append(result)
    return results


# --- reading --------------------------------------------------------------------------------


def status(con: oracledb.Connection) -> list[tuple]:
    """Per series: current periods, closed revisions, files loaded, first and last period, and
    the last successful load (UTC)."""
    with con.cursor() as cur:
        cur.execute(
            """
            SELECT s.series_key,
                   (SELECT COUNT(*) FROM observation_current c WHERE c.series_key = s.series_key),
                   (SELECT COUNT(*) FROM observation_revision r
                     WHERE r.series_key = s.series_key AND r.known_to IS NOT NULL),
                   (SELECT COUNT(*) FROM landed_file f WHERE f.series_key = s.series_key),
                   (SELECT MIN(ref_date) FROM observation_current c
                     WHERE c.series_key = s.series_key),
                   (SELECT MAX(ref_date) FROM observation_current c
                     WHERE c.series_key = s.series_key),
                   (SELECT MAX(finished_at) FROM load_audit a
                     WHERE a.series_key = s.series_key AND a.status = 'success')
            FROM series s
            ORDER BY s.series_key
            """
        )
        return cur.fetchall()


def query(con: oracledb.Connection, statement: str) -> tuple[list[str] | None, list[tuple]]:
    with con.cursor() as cur:
        cur.execute(statement.strip().rstrip(";"))
        if not cur.description:
            return None, []
        return [d[0].lower() for d in cur.description], cur.fetchall()


@dataclass(frozen=True)
class SeriesProfile:
    rows: int
    first: object
    last: object
    total: float


def profile_oracle(con: oracledb.Connection) -> dict[str, SeriesProfile]:
    _, rows = query(
        con,
        "SELECT series_key, COUNT(*), MIN(ref_date), MAX(ref_date), SUM(value) "
        "FROM observation_current GROUP BY series_key",
    )
    return {k: SeriesProfile(n, _as_date(a), _as_date(b), float(t)) for k, n, a, b, t in rows}


def profile_duckdb(con) -> dict[str, SeriesProfile]:
    rows = con.execute(
        "SELECT series_key, count(*), min(ref_date), max(ref_date), sum(value) "
        "FROM raw.observations GROUP BY series_key"
    ).fetchall()
    return {k: SeriesProfile(n, a, b, float(t)) for k, n, a, b, t in rows}


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def compare(oracle: dict[str, SeriesProfile], duck: dict[str, SeriesProfile]) -> list[tuple]:
    """Basic check per series: row count, first and last period, and the sum of values
    (rounded to 6 decimals: DuckDB holds doubles, Oracle exact decimals). Full reconciliation
    (fingerprints, schema drift, report) is M6."""
    rows = []
    for key in sorted(set(oracle) | set(duck)):
        o, d = oracle.get(key), duck.get(key)
        same = (
            o is not None
            and d is not None
            and (o.rows, o.first, o.last) == (d.rows, d.first, d.last)
            and round(o.total, 6) == round(d.total, 6)
        )
        rows.append((key, o, d, "match" if same else "MISMATCH"))
    return rows
