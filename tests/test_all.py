import os, tempfile
import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(monkeypatch, tmp_path):
    from jobhunter import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    from jobhunter import collectors
    r = collectors.ingest(collectors.from_json_file("data/sample_jobs.json"), min_score=10)
    assert r["added"] > 0
    from jobhunter.api import app
    return TestClient(app)

def test_classify_gps_high():
    from jobhunter.classify import classify
    r = classify("GNSS/GPS 수신기 펌웨어 개발자", "NMEA RTK 임베디드 C++")
    assert r["score"] >= 70 and r["categories"][0] == "gps"

def test_classify_irrelevant_low():
    from jobhunter.classify import classify
    assert classify("해외영업 마케팅 담당", "영업 및 마케팅")["score"] == 0

def test_short_keyword_word_boundary():
    from jobhunter.classify import classify
    assert "rf" not in classify("surf shop manager", "")["matched"]

def test_filter_and_dedupe(client):
    jobs = client.get("/api/jobs?min_score=10").json()
    titles = [j["title"] for j in jobs]
    assert not any("회계" in t or "디자이너" in t for t in titles)
    from jobhunter import collectors
    again = collectors.ingest(collectors.from_json_file("data/sample_jobs.json"), min_score=10)
    assert again["added"] == 0

def test_sorted_by_score(client):
    s = [j["score"] for j in client.get("/api/jobs").json()]
    assert s == sorted(s, reverse=True)

def test_status_update_and_validation(client):
    jid = client.get("/api/jobs").json()[0]["id"]
    assert client.patch(f"/api/jobs/{jid}", json={"status": "applied"}).status_code == 200
    assert client.patch(f"/api/jobs/{jid}", json={"status": "bogus"}).status_code == 400
    assert client.patch("/api/jobs/99999", json={"status": "applied"}).status_code == 404
    assert client.get("/api/stats").json()["by_status"]["applied"] == 1

def test_deadlines_and_ics(client):
    assert len(client.get("/api/deadlines?days=7").json()) >= 1
    ics = client.get("/api/calendar.ics").text
    assert ics.startswith("BEGIN:VCALENDAR") and "[마감]" in ics

def test_mail_detect():
    from jobhunter.integrations import detect_status_from_mail as d
    assert d("[A사] 서류 합격 및 면접 안내") == "interview"
    assert d("전형 결과 안내", "아쉽게도 불합격하셨습니다") == "rejected"
    assert d("최종 합격을 축하드립니다") == "offer"
    assert d("뉴스레터") is None

def test_notion_payload():
    from jobhunter.integrations import to_notion_properties
    p = to_notion_properties({"title": "x", "url": "http://a", "score": 50, "deadline": "2026-12-01"})
    assert p["마감일"]["date"]["start"] == "2026-12-01"

def test_bot_texts(client):
    from jobhunter import bot
    assert "http" in bot.top_text()
    assert "전체" in bot.stats_text()

def test_dashboard_served(client):
    assert "Job Hunt Board" in client.get("/").text
