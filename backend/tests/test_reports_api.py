"""报告页两栏口径：当前栏即时计算不落库，历史栏仅存档，两边共用同一边界规则。"""
import os
import tempfile

# 必须在导入 app 之前指向独立的 sqlite 库，避免引擎绑定到配置里的 postgres
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="busgap_test_"), "test.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # 进入 lifespan：建表 + 种子数据
        yield c


def test_live_events_do_not_persist(client):
    before = client.get("/api/reports").json()
    resp = client.get("/api/reports/live", params={"line_id": 1})
    assert resp.status_code == 200
    assert resp.json()["events"]  # 种子数据里存在间隔事件
    assert len(client.get("/api/reports").json()) == len(before)  # 即时计算不落库


def test_run_detection_persists_history(client):
    before = client.get("/api/reports").json()
    resp = client.post("/api/reports/run", params={"line_id": 1})
    assert resp.status_code == 200
    rid = resp.json()["id"]
    after = client.get("/api/reports").json()
    assert len(after) == len(before) + 1
    assert after[0]["id"] == rid  # 列表按 id 倒序，最新存档在最前


def test_suggestions_do_not_persist(client):
    before = client.get("/api/reports").json()
    resp = client.get("/api/reports/suggestions", params={"line_id": 1})
    assert resp.status_code == 200
    assert all(e["status"] != "normal" for e in resp.json()["suggestions"])
    assert len(client.get("/api/reports").json()) == len(before)


def test_live_events_match_timeline_marks(client):
    # 当前栏每一条事件的前后班次，都能在对应站点的时间轴上找到班次点
    events = client.get("/api/reports/live", params={"line_id": 1}).json()["events"]
    assert events
    for e in events:
        marks = client.get("/api/reports/timeline",
                           params={"line_id": 1, "stop_name": e["stop_name"]}).json()["marks"]
        trip_nos = {m["trip_no"] for m in marks}
        assert e["earlier_trip"] in trip_nos
        assert e["later_trip"] in trip_nos


def test_timeline_not_affected_by_history_reports(client):
    # 历史报告不参与当前时间轴画点
    params = {"line_id": 1, "stop_name": "市民中心"}
    before = client.get("/api/reports/timeline", params=params).json()
    client.post("/api/reports/run", params={"line_id": 1})
    assert client.get("/api/reports/timeline", params=params).json() == before
