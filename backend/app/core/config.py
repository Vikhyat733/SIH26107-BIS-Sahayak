from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
STANDARDS_DIR = DATA_DIR / "standards"
QCO_FILE = DATA_DIR / "qco" / "qco_registry.json"
DEMO_REPORTS_DIR = DATA_DIR / "demo_reports"
