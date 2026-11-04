"""SQLite 저장소 (표준 라이브러리만 사용)."""
from __future__ import annotations
import json, os, sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("JOBHUNT_DB", "jobhunt.db")
STATUSES = ["interested", "applied", "document_pass", "interview", "offer", "rejected"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT, url TEXT UNIQUE, title TEXT NOT NULL, company TEXT,
  location TEXT, description TEXT, deadline TEXT,
  score INTEGER DEFAULT 0, categories TEXT DEFAULT '[]', matched TEXT DEFAULT '[]',
  status TEXT DEFAULT 'interested', notes TEXT DEFAULT '',
  interview_at TEXT, notified INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_usage(
  day TEXT, source TEXT, n INTEGER DEFAULT 0, PRIMARY KEY(day, source)
);
"""


@contextmanager
def conn(path: str | None = None):
    c = sqlite3.connect(path or DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("categories", "matched"):
        if k in d:
            d[k] = json.loads(d[k] or "[]")
    return d


def upsert_job(c, job: dict) -> bool:
    """URL 기준 중복 제거. 새로 추가되면 True."""
    if c.execute("SELECT 1 FROM jobs WHERE url=?", (job["url"],)).fetchone():
        return False
    c.execute(
        "INSERT INTO jobs(source,url,title,company,location,description,deadline,score,categories,matched)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (job.get("source"), job["url"], job["title"], job.get("company"), job.get("location"),
         job.get("description"), job.get("deadline"), job.get("score", 0),
         json.dumps(job.get("categories", []), ensure_ascii=False),
         json.dumps(job.get("matched", []), ensure_ascii=False)),
    )
    return True
