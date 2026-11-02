import pytest

from cdm import cli


@pytest.mark.parametrize(
    "command",
    [["status"], ["sql", "SELECT 1"], ["dbt", "build"], ["run", "--skip-ingest"]],
)
def test_missing_warehouse_says_how_to_create_it(tmp_path, capsys, command):
    db_path = tmp_path / "warehouse.duckdb"
    assert cli.main(["--db", str(db_path), *command]) == 1
    assert "uv run cdm run" in capsys.readouterr().err
    assert not db_path.exists()  # nothing created as a side effect


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["dbt", "--version"], (["dbt"], ["--version"])),
        (["--db", "x.duckdb", "dbt", "build", "-s", "dim_date"],
         (["--db", "x.duckdb", "dbt"], ["build", "-s", "dim_date"])),
        (["sql", "SELECT 'dbt'"], (["sql", "SELECT 'dbt'"], [])),
        (["status"], (["status"], [])),
    ],
)  # fmt: skip
def test_everything_after_dbt_goes_to_dbt(argv, expected):
    assert cli._split_dbt_args(argv) == expected
