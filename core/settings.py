"""全局路径常量与项目根目录解析。"""
from __future__ import annotations

from pathlib import Path

BASE_DIR: Path = Path(__file__).parent.parent

CONFIG_DIR: Path = BASE_DIR / "config"
DATA_DIR: Path = BASE_DIR / "data"
TEMPLATES_DIR: Path = DATA_DIR / "templates"
SCHEMAS_DIR: Path = DATA_DIR / "schemas"
OUTPUTS_DIR: Path = BASE_DIR / "outputs"
LOGS_DIR: Path = OUTPUTS_DIR / "logs"
ALLURE_RESULTS_DIR: Path = OUTPUTS_DIR / "allure_results"

for _d in (LOGS_DIR, ALLURE_RESULTS_DIR, OUTPUTS_DIR / "screenshots"):
    _d.mkdir(parents=True, exist_ok=True)
