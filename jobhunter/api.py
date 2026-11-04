from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from . import db, integrations, collectors

app = FastAPI(title="Job Hunt Command Center")
STATIC = Path(__file__).parent / "static"


class JobUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    interview_at: str | None = None
    deadline: str | None = None


class MailIn(BaseModel):
    subject: str
    body: str = ""
    job_id: int | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/jobs")
def list_jobs(status: str | None = None, category: str | None = None,
              min_score: int = 0, q: str | None = None, limit: int = Query(200, le=1000)):
    sql, args = "SELECT * FROM jobs WHERE score>=?", [min_score]
    if status:
        sql += " AND status=?"; args.append(status)
    if q:
        sql += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"; args += [f"%{q}%"] * 3
    sql += " ORDER BY score DESC, deadline IS NULL, deadline LIMIT ?"; args.append(limit)
    with db.conn() as c:
        rows = [db.row_to_dict(r) for r in c.execute(sql, args)]
    if category:
        rows = [r for r in rows if category in r["categories"]]
    return rows


@app.patch("/api/jobs/{job_id}")
def update_job(job_id: int, body: JobUpdate):
    fields = body.model_dump(exclude_none=True)
    if "status" in fields and fields["status"] not in db.STATUSES:
        raise HTTPException(400, f"status must be one of {db.STATUSES}")
    if not fields:
        raise HTTPException(400, "nothing to update")
    with db.conn() as c:
        cur = c.execute(f"UPDATE jobs SET {', '.join(k + '=?' for k in fields)} WHERE id=?",
                        [*fields.values(), job_id])
        if not cur.rowcount:
            raise HTTPException(404, "job not found")
    return {"ok": True}


@app.get("/api/stats")
def stats():
    with db.conn() as c:
        by_status = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status")}
        total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        rows = [db.row_to_dict(r) for r in c.execute("SELECT categories FROM jobs")]
    cats: dict[str, int] = {}
    for r in rows:
        for cat in r["categories"][:1]:
            cats[cat] = cats.get(cat, 0) + 1
    return {"total": total, "by_status": by_status, "by_category": cats}


@app.get("/api/deadlines")
def deadlines(days: int = 7):
    today = date.today()
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs WHERE deadline BETWEEN ? AND ? AND status IN ('interested','applied') ORDER BY deadline",
            (today.isoformat(), (today + timedelta(days=days)).isoformat()))
        return [db.row_to_dict(r) for r in rows]


@app.get("/api/calendar.ics", response_class=PlainTextResponse)
def calendar_ics():
    with db.conn() as c:
        jobs = [db.row_to_dict(r) for r in c.execute(
            "SELECT * FROM jobs WHERE deadline IS NOT NULL OR interview_at IS NOT NULL")]
    return PlainTextResponse(integrations.to_ics(jobs), media_type="text/calendar")


@app.post("/api/mail/detect")
def mail_detect(m: MailIn):
    """메일 제목/본문으로 상태를 추정. job_id를 주면 자동 반영."""
    status = integrations.detect_status_from_mail(m.subject, m.body)
    if status and m.job_id:
        with db.conn() as c:
            c.execute("UPDATE jobs SET status=? WHERE id=?", (status, m.job_id))
    return {"status": status}


@app.post("/api/collect/file")
def collect_file(path: str, min_score: int = 10):
    return collectors.ingest(collectors.from_json_file(path), min_score=min_score)
