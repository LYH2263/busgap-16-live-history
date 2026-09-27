import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, events_to_dicts
router = APIRouter(prefix="/reports", tags=["reports"])

def compute_line_events(db: Session, line_id: int, stop_name: str | None) -> tuple[Line, list[dict]]:
    """按当前班次与到站即时算出间隔事件。

    分类只走 bunch_engine.classify_gap（现网边界规则：间隔恰好等于阈值判正常），
    run / current / suggestions 共用此入口，避免各处各算各的。
    """
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    events = detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold)
    return line, events_to_dicts(events)

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    return [{"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
             "created_at": r.created_at.isoformat(), "events": json.loads(r.summary_json)} for r in rows]

@router.get("/current")
def current_events(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    """当前栏数据源：即时计算，不落库，不产生历史报告。"""
    line, data = compute_line_events(db, line_id, stop_name)
    return {"line_id": line.id, "stop_name": stop_name or "*", "events": data}

@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line, data = compute_line_events(db, line_id, stop_name)
    report = BunchReport(line_id=line.id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}

@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    _, data = compute_line_events(db, line_id, None)
    return {"line_id": line_id, "suggestions": [e for e in data if e["status"] != "normal"]}

@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": []}
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    marks = [{"trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive.isoformat(),
              "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2)} for a in arrivals]
    return {"stop_name": stop_name, "marks": marks}
