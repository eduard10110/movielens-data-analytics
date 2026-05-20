from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
ETL_APP = ROOT / "team_member_3_etl_pipeline" / "app"
INTEGRATED_APP = ROOT / "final_integrated_project" / "app"


def _app_dir() -> Path:
    if ETL_APP.exists():
        return ETL_APP
    if INTEGRATED_APP.exists():
        return INTEGRATED_APP
    pytest.skip("ETL app/ directory not found")


@pytest.mark.parametrize(
    "module,func",
    [
        ("extract.py", "def run_extract"),
        ("transform.py", "def run_transform"),
        ("load.py", "def run_load"),
        ("main.py", "def run_pipeline"),
        ("utils.py", "def get_engine"),
    ],
)
def test_etl_module_contract(module: str, func: str):
    path = _app_dir() / module
    assert path.exists(), f"Missing {module}"
    source = path.read_text(encoding="utf-8")
    assert func in source, f"{module} must define {func}"
