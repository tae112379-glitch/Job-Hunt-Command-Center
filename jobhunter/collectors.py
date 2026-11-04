"""공고 수집기. 모든 수집기는 dict 리스트(title,url,company,...)를 반환한다.

주의: robots.txt / 이용약관이 허용하는 RSS·공식 API·직접 내려받은 파일만 사용할 것.
"""
from __future__ import annotations
import json, re
from pathlib import Path
import feedparser
import httpx
from .classify import classify
from . import db

UA = "JobHuntBot/0.1 (personal job tracker)"


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def from_rss(url: str, source: str | None = None) -> list[dict]:
    resp = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
    return [{
        "source": source or url, "url": e.get("link"), "title": e.get("title", ""),
        "company": e.get("author"), "description": _strip_html(e.get("summary", "")),
    } for e in feed.entries if e.get("link")]


def from_json_file(path: str, source: str = "file") -> list[dict]:
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{**i, "source": i.get("source", source)} for i in items]


def from_json_api(url: str, mapping: dict, source: str, list_key: str | None = None) -> list[dict]:
    """공개 JSON API용 범용 어댑터. mapping 예: {'title':'title','url':'link','company':'company'}"""
    resp = httpx.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    rows = data[list_key] if list_key else data
    return [{"source": source, **{k: r.get(v) for k, v in mapping.items()}} for r in rows]


def ingest(jobs: list[dict], min_score: int = 0, path: str | None = None) -> dict:
    """분류 후 저장. min_score 미만은 버린다."""
    added = skipped = 0
    with db.conn(path) as c:
        for j in jobs:
            if not j.get("url") or not j.get("title"):
                continue
            j.update(classify(j["title"], j.get("description") or ""))
            if j["score"] < min_score:
                skipped += 1
                continue
            added += db.upsert_job(c, j)
    return {"added": added, "filtered_out": skipped, "total_seen": len(jobs)}
