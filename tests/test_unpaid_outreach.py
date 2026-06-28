from datetime import datetime, timedelta

from services.unpaid_outreach_service import UnpaidOutreachService


def test_outreach_pitch_then_ghost_then_pix(tmp_path):
    svc = UnpaidOutreachService(data_file=str(tmp_path / "outreach.json"))
    user_id = 12345
    t0 = datetime(2026, 6, 27, 10, 0, 0)

    assert svc.decide_action(user_id, t0) == "pitch"
    svc.record_pitch(user_id, t0)

    assert svc.decide_action(user_id, t0 + timedelta(hours=1)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(hours=23)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(hours=24)) == "pix"

    svc.record_pix(user_id, t0 + timedelta(hours=24))
    assert svc.decide_action(user_id, t0 + timedelta(hours=25)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(hours=48)) == "pitch"


def test_outreach_persists(tmp_path):
    path = tmp_path / "outreach.json"
    svc1 = UnpaidOutreachService(data_file=str(path))
    t0 = datetime(2026, 6, 27, 10, 0, 0)
    svc1.record_pitch(999, t0)

    svc2 = UnpaidOutreachService(data_file=str(path))
    assert svc2.decide_action(999, t0 + timedelta(hours=1)) == "ghost"
