from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_classify_boundary_values_are_normal():
    # 现网边界规则：间隔恰好等于阈值时不算异常，当前栏与历史栏同此口径
    assert classify_gap(3.0, 8.0, 3.0, 15.0)[0] == "normal"
    assert classify_gap(15.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_boundary_gap_event_normal():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=3)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert [e.status for e in events] == ["normal"]

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"
