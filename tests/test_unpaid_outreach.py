from datetime import datetime, timedelta

from services.unpaid_outreach_service import UnpaidOutreachService, GHOSTING_HOURS


def test_outreach_pitch_pix_then_ghost_then_repeat(tmp_path):
    svc = UnpaidOutreachService(data_file=str(tmp_path / "outreach.json"))
    user_id = 12345
    t0 = datetime(2026, 6, 27, 10, 0, 0)

    assert svc.decide_action(user_id, t0) == "pitch_pix"
    svc.record_outreach(user_id, t0)

    assert svc.decide_action(user_id, t0 + timedelta(minutes=30)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(minutes=59)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(hours=GHOSTING_HOURS)) == "pitch_pix"

    svc.record_outreach(user_id, t0 + timedelta(hours=GHOSTING_HOURS))
    assert svc.decide_action(user_id, t0 + timedelta(hours=GHOSTING_HOURS, minutes=30)) == "ghost"
    assert svc.decide_action(user_id, t0 + timedelta(hours=GHOSTING_HOURS * 2)) == "pitch_pix"


def test_outreach_persists(tmp_path):
    path = tmp_path / "outreach.json"
    svc1 = UnpaidOutreachService(data_file=str(path))
    t0 = datetime(2026, 6, 27, 10, 0, 0)
    svc1.record_outreach(999, t0)

    svc2 = UnpaidOutreachService(data_file=str(path))
    assert svc2.decide_action(999, t0 + timedelta(minutes=30)) == "ghost"
