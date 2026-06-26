import asyncio
from datetime import date, datetime

import services.propaganda_service as ps


# --- split_message ---

def test_split_message_short_returns_single():
    assert ps.split_message("oi") == ["oi"]


def test_split_message_respects_limit_multi_paragraph():
    text = "\n\n".join(f"P{i} " + "x" * 500 for i in range(20))
    chunks = ps.split_message(text, limit=4000)
    assert len(chunks) > 1
    assert all(len(c) <= 4000 for c in chunks)
    assert "P0" in chunks[0]
    assert "P19" in chunks[-1]


def test_split_message_hard_splits_long_paragraph():
    long = "y" * 9000
    chunks = ps.split_message(long, limit=4000)
    assert all(len(c) <= 4000 for c in chunks)
    assert "".join(chunks) == long


# --- next_run ---

def test_next_run_today_when_before_9am():
    now = datetime(2026, 6, 25, 8, 30, tzinfo=ps.BRAZIL_TZ)
    nxt = ps.next_run(now)
    assert (nxt.year, nxt.month, nxt.day, nxt.hour, nxt.minute) == (2026, 6, 25, 9, 0)


def test_next_run_tomorrow_when_after_9am():
    now = datetime(2026, 6, 25, 10, 0, tzinfo=ps.BRAZIL_TZ)
    nxt = ps.next_run(now)
    assert (nxt.year, nxt.month, nxt.day, nxt.hour) == (2026, 6, 26, 9)


# --- _should_send ---

def test_should_send_dedup_per_day():
    svc = ps.DailyBroadcastService()
    svc.last_sent_date = date(2026, 6, 25)
    assert svc._should_send(date(2026, 6, 25)) is False
    assert svc._should_send(date(2026, 6, 26)) is True


# --- send_daily_broadcast ---

def _patch_bot_and_digest(monkeypatch, digest_value):
    sent = []

    async def fake_send(chat_id, text, **kw):
        sent.append((chat_id, text, kw.get("parse_mode")))

    async def fake_digest():
        return digest_value

    monkeypatch.setattr(ps.bot, "send_message", fake_send)
    monkeypatch.setattr(ps, "generate_news_digest", fake_digest)
    return sent


def test_broadcast_friday_sends_news_then_ad(monkeypatch):
    sent = _patch_bot_and_digest(monkeypatch, "NEWS")
    svc = ps.DailyBroadcastService()
    friday = datetime(2026, 6, 26, 9, 0, tzinfo=ps.BRAZIL_TZ)
    asyncio.run(svc.send_daily_broadcast(now=friday))
    assert len(sent) == 2
    assert sent[0][1] == "NEWS"
    assert "promoção" in sent[1][1].lower()
    assert all(cid == ps.VESTIBULARES_GROUP_ID for cid, _, _ in sent)


def test_broadcast_non_friday_only_news(monkeypatch):
    sent = _patch_bot_and_digest(monkeypatch, "NEWS")
    svc = ps.DailyBroadcastService()
    thursday = datetime(2026, 6, 25, 9, 0, tzinfo=ps.BRAZIL_TZ)
    asyncio.run(svc.send_daily_broadcast(now=thursday))
    assert len(sent) == 1
    assert sent[0][1] == "NEWS"


def test_broadcast_skips_news_when_digest_none(monkeypatch):
    sent = _patch_bot_and_digest(monkeypatch, None)
    svc = ps.DailyBroadcastService()
    friday = datetime(2026, 6, 26, 9, 0, tzinfo=ps.BRAZIL_TZ)
    asyncio.run(svc.send_daily_broadcast(now=friday))
    assert len(sent) == 1
    assert "promoção" in sent[0][1].lower()


def test_broadcast_dedupes_same_day(monkeypatch):
    sent = _patch_bot_and_digest(monkeypatch, "NEWS")
    svc = ps.DailyBroadcastService()
    thursday = datetime(2026, 6, 25, 9, 0, tzinfo=ps.BRAZIL_TZ)
    asyncio.run(svc.send_daily_broadcast(now=thursday))
    asyncio.run(svc.send_daily_broadcast(now=thursday))
    assert len(sent) == 1  # segundo envio é ignorado


# --- fallback de Markdown ---

def test_send_to_group_falls_back_to_plain(monkeypatch):
    calls = []

    async def fake_send(chat_id, text, **kw):
        calls.append(kw.get("parse_mode"))
        if kw.get("parse_mode") == "Markdown":
            raise Exception("can't parse entities")

    monkeypatch.setattr(ps.bot, "send_message", fake_send)
    svc = ps.DailyBroadcastService()
    asyncio.run(svc._send_to_group("*texto quebrado"))
    assert calls == ["Markdown", None]
