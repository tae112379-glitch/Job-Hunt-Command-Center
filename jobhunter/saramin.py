"""사람인 Open API 어댑터 (https://oapi.saramin.co.kr/job-search).

- 키는 환경변수 SARAMIN_ACCESS_KEY 로만 받는다 (코드/저장소에 넣지 말 것).
- 이용 목적에 쓴 약속을 코드로 지키기 위해 하루 호출 상한(SARAMIN_DAILY_LIMIT, 기본 20)을 둔다.
- 응답 필드는 공개 문서 기준으로 작성했으며, 실제 키 발급 후 첫 호출로 반드시 검증할 것.
- 공고 원문 링크는 사람인 페이지 URL 그대로 사용한다 (출처 표기).
"""
from __future__ import annotations
import os
from datetime import date, datetime, timezone
import httpx
from . import db

ENDPOINT = "https://oapi.saramin.co.kr/job-search"
DEFAULT_KEYWORDS = ["GPS", "GNSS", "네트워크 엔지니어", "임베디드", "펌웨어", "통신 프로토콜"]


class RateLimitExceeded(RuntimeError):
    pass


def daily_limit() -> int:
    return int(os.environ.get("SARAMIN_DAILY_LIMIT", "20"))


def _consume_call(path: str | None = None) -> None:
    today = date.today().isoformat()
    with db.conn(path) as c:
        c.execute("INSERT OR IGNORE INTO api_usage(day, source, n) VALUES(?, 'saramin', 0)", (today,))
        n = c.execute("SELECT n FROM api_usage WHERE day=? AND source='saramin'", (today,)).fetchone()[0]
        if n >= daily_limit():
            raise RateLimitExceeded(f"사람인 하루 호출 상한({daily_limit()}회) 도달")
        c.execute("UPDATE api_usage SET n=n+1 WHERE day=? AND source='saramin'", (today,))


def build_params(keyword: str, access_key: str, count: int = 50, start: int = 0) -> dict:
    return {"access-key": access_key, "keywords": keyword, "count": count, "start": start, "sort": "pd"}


def _ts_to_date(ts) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def parse_response(data: dict) -> list[dict]:
    """사람인 JSON 응답 → 내부 공고 dict 리스트. 필드가 비어 있어도 죽지 않는다."""
    out = []
    for j in (data.get("jobs") or {}).get("job", []) or []:
        pos = j.get("position") or {}
        comp = ((j.get("company") or {}).get("detail")) or {}
        url = j.get("url")
        title = pos.get("title")
        if not url or not title:
            continue
        desc = " ".join(filter(None, [
            j.get("keyword"), (pos.get("job-mid-code") or {}).get("name"),
            (pos.get("job-type") or {}).get("name"), (pos.get("experience-level") or {}).get("name"),
        ]))
        out.append({
            "source": "saramin", "url": url, "title": title,
            "company": comp.get("name"),
            "location": (pos.get("location") or {}).get("name"),
            "description": desc,
            "deadline": _ts_to_date(j.get("expiration-timestamp")),
        })
    return out


def fetch(keyword: str, access_key: str | None = None, client: httpx.Client | None = None,
          db_path: str | None = None) -> list[dict]:
    key = access_key or os.environ.get("SARAMIN_ACCESS_KEY")
    if not key:
        raise RuntimeError("SARAMIN_ACCESS_KEY 환경변수가 필요합니다.")
    _consume_call(db_path)
    c = client or httpx.Client(timeout=20)
    r = c.get(ENDPOINT, params=build_params(keyword, key), headers={"Accept": "application/json"})
    r.raise_for_status()
    return parse_response(r.json())


def collect(keywords: list[str] | None = None, min_score: int = 10, db_path: str | None = None) -> dict:
    from .collectors import ingest
    total = {"added": 0, "filtered_out": 0, "total_seen": 0, "stopped_by_limit": False}
    for kw in keywords or DEFAULT_KEYWORDS:
        try:
            res = ingest(fetch(kw, db_path=db_path), min_score=min_score, path=db_path)
        except RateLimitExceeded:
            total["stopped_by_limit"] = True
            break
        for k in ("added", "filtered_out", "total_seen"):
            total[k] += res[k]
    return total
