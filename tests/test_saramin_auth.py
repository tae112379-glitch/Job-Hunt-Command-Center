import base64
import pytest
from fastapi.testclient import TestClient

SAMPLE = {"jobs": {"count": 2, "job": [
    {"url": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=1", "keyword": "GPS, 펌웨어, C++",
     "company": {"detail": {"name": "정밀측위"}},
     "position": {"title": "GNSS 수신기 펌웨어 개발", "location": {"name": "서울 &gt; 강남구"},
                  "job-mid-code": {"name": "임베디드"}, "experience-level": {"name": "신입"}},
     "expiration-timestamp": "1893456000"},
    {"url": None, "position": {"title": "url 없는 공고"}},          # 건너뛰어야 함
    {"url": "https://x/2", "position": {"title": "영업 마케팅 담당"}},  # 필터로 걸러짐
]}}


@pytest.fixture()
def dbpath(monkeypatch, tmp_path):
    from jobhunter import db
    p = str(tmp_path / "s.db")
    monkeypatch.setattr(db, "DB_PATH", p)
    return p


def test_parse_response():
    from jobhunter.saramin import parse_response
    jobs = parse_response(SAMPLE)
    assert len(jobs) == 2 and jobs[0]["company"] == "정밀측위"
    assert jobs[0]["deadline"] == "2030-01-01" and "GPS" in jobs[0]["description"]
    assert parse_response({}) == [] and parse_response({"jobs": {"job": None}}) == []


def test_rate_limit(dbpath, monkeypatch):
    from jobhunter import saramin
    monkeypatch.setenv("SARAMIN_DAILY_LIMIT", "2")
    saramin._consume_call(dbpath); saramin._consume_call(dbpath)
    with pytest.raises(saramin.RateLimitExceeded):
        saramin._consume_call(dbpath)


def test_collect_with_fake_http(dbpath, monkeypatch):
    import httpx
    from jobhunter import saramin
    monkeypatch.setenv("SARAMIN_ACCESS_KEY", "k")
    calls = []
    def handler(req):
        calls.append(req.url.params["keywords"])
        assert req.url.params["access-key"] == "k"
        return httpx.Response(200, json=SAMPLE)
    real = httpx.Client
    monkeypatch.setattr(saramin.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler)))
    res = saramin.collect(["GPS", "네트워크"], db_path=dbpath)
    assert calls == ["GPS", "네트워크"] and res["added"] == 1   # 두 번째 키워드는 중복 URL


def test_collect_stops_at_limit(dbpath, monkeypatch):
    import httpx
    from jobhunter import saramin
    monkeypatch.setenv("SARAMIN_ACCESS_KEY", "k"); monkeypatch.setenv("SARAMIN_DAILY_LIMIT", "1")
    real = httpx.Client
    monkeypatch.setattr(saramin.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=SAMPLE))))
    assert saramin.collect(["a", "b", "c"], db_path=dbpath)["stopped_by_limit"] is True


def test_missing_key(monkeypatch):
    from jobhunter import saramin
    monkeypatch.delenv("SARAMIN_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError):
        saramin.fetch("gps")


def _basic(u, p): return {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}


def test_auth_flow(dbpath, monkeypatch):
    monkeypatch.setenv("JOBHUNT_PASSWORD", "s3cret")
    from jobhunter.api import app
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200            # 헬스체크는 공개
    assert c.get("/api/jobs").status_code == 401
    assert c.get("/").status_code == 401
    assert c.get("/api/jobs", headers=_basic("admin", "wrong")).status_code == 401
    assert c.get("/api/jobs", headers=_basic("admin", "s3cret")).status_code == 200
    assert c.get("/api/jobs", headers={"Authorization": "Basic %%%"}).status_code == 401


def test_production_requires_password(monkeypatch):
    from jobhunter import auth
    monkeypatch.setenv("JOBHUNT_ENV", "production"); monkeypatch.delenv("JOBHUNT_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        auth.check_startup()
