"""캘린더(.ics) 내보내기, Notion 페이로드, 메일 상태 판별.

외부 서비스 호출 없이 순수 함수로 구성 → 어디서든 테스트 가능.
실제 API 연결(구글 캘린더/Notion/Gmail)은 이 출력을 각 클라이언트에 넘기면 된다.
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone

# 메일 제목/본문 → 지원 상태 (구체적인 것 먼저)
_MAIL_RULES = [
    ("offer", r"최종\s*합격|합격을?\s*축하|입사\s*제안|offer"),
    ("rejected", r"불합격|아쉽게도|전형.*종료|not\s+(?:been\s+)?selected|unfortunately"),
    ("interview", r"면접\s*(?:안내|일정|전형)|interview"),
    ("document_pass", r"서류\s*(?:전형\s*)?합격|서류.*통과|코딩\s*테스트\s*안내|과제\s*전형"),
    ("applied", r"지원이?\s*(?:완료|접수)|application\s+received"),
]


def detect_status_from_mail(subject: str, body: str = "") -> str | None:
    text = f"{subject}\n{body}".lower()
    for status, pat in _MAIL_RULES:
        if re.search(pat, text):
            return status
    return None


def _ics_dt(s: str) -> str:
    dt = datetime.fromisoformat(s)
    return dt.strftime("%Y%m%dT%H%M%S") if "T" in s or " " in s else dt.strftime("%Y%m%d")


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(jobs: list[dict]) -> str:
    """마감일(종일)·면접일시 이벤트를 담은 .ics 문자열 (구글 캘린더에서 가져오기 가능)."""
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//JobHunt//KO//", "CALSCALE:GREGORIAN"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def event(uid, summary, start, desc, allday):
        out.extend(["BEGIN:VEVENT", f"UID:{uid}@jobhunt", f"DTSTAMP:{stamp}"])
        if allday:
            end = (datetime.fromisoformat(start) + timedelta(days=1)).strftime("%Y%m%d")
            out.extend([f"DTSTART;VALUE=DATE:{_ics_dt(start)}", f"DTEND;VALUE=DATE:{end}"])
        else:
            end = (datetime.fromisoformat(start) + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")
            out.extend([f"DTSTART:{_ics_dt(start)}", f"DTEND:{end}"])
        out.extend([f"SUMMARY:{_esc(summary)}", f"DESCRIPTION:{_esc(desc)}", "END:VEVENT"])

    for j in jobs:
        who = f"{j.get('company') or ''} {j['title']}".strip()
        if j.get("deadline"):
            event(f"dl-{j['id']}", f"[마감] {who}", j["deadline"], j.get("url", ""), True)
        if j.get("interview_at"):
            event(f"iv-{j['id']}", f"[면접] {who}", j["interview_at"], j.get("url", ""), False)
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def to_notion_properties(job: dict) -> dict:
    """Notion 데이터베이스 행 생성용 속성(공식 API 형식)."""
    props = {
        "이름": {"title": [{"text": {"content": job["title"]}}]},
        "회사": {"rich_text": [{"text": {"content": job.get("company") or ""}}]},
        "상태": {"select": {"name": job.get("status", "interested")}},
        "적합도": {"number": job.get("score", 0)},
        "링크": {"url": job.get("url")},
    }
    if job.get("deadline"):
        props["마감일"] = {"date": {"start": job["deadline"]}}
    return props
