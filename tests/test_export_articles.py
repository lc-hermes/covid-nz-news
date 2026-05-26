import os
import subprocess
import json
import csv
from pathlib import Path

# Prepare a temporary database
DB_PATH = Path("tmp_export_db.sqlite")
if DB_PATH.exists():
    DB_PATH.unlink()

import sqlite3
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT,
    source_domain TEXT,
    crawl_id TEXT,
    timestamp TEXT,
    language TEXT,
    status_code TEXT
)
""")
cursor.execute("INSERT INTO articles (url, title, content, source_domain, crawl_id, timestamp, language, status_code) VALUES (?,?,?,?,?,?,?,?)",
               ("https://example.com", "Example", "Example content", "example.com", "test", "2024-01-01", "en", "200"))
conn.commit()
conn.close()

# Patch settings to point to this DB by modifying settings
import importlib.util
spec = importlib.util.spec_from_file_location("settings", str(Path("settings.py")))
settings_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_mod)
settings_mod.settings.database.path = str(DB_PATH)
# ensure settings is importable
import sys
sys.modules["settings"] = settings_mod

# Run export script via subprocess
cmd = ["python", "scripts/export_articles.py"]
subprocess.run(cmd, check=True)

# Verify outputs
OUTPUT_DIR = Path("export_output")
assert OUTPUT_DIR.exists(), "Output dir missing"
csv_path = OUTPUT_DIR / "articles.csv"
json_path = OUTPUT_DIR / "articles.json"
assert csv_path.exists(), "CSV missing"
assert json_path.exists(), "JSON missing"

# Verify CSV content
with csv_path.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
assert len(rows) == 1, "CSV should contain one row"
assert rows[0]["url"] == "https://example.com"

# Verify JSON content
with json_path.open("r", encoding="utf-8") as f:
    data = json.load(f)
assert isinstance(data, list)
assert len(data) == 1
assert data[0]["url"] == "https://example.com"

# cleanup
import shutil
shutil.rmtree(OUTPUT_DIR)
DB_PATH.unlink()
print("test_export_articles passed")
