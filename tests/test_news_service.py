import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import config
import services.news_service as news_service


def test_build_news_input_has_date_and_themes():
    text = news_service.build_news_input(date(2026, 6, 25))
    assert "25/06/2026" in text
    assert "Praticante de Prático" in text


def test_generate_news_digest_returns_stripped_text(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.output_text = "  📋 notícias do dia  "
    fake_create = AsyncMock(return_value=fake_resp)
    monkeypatch.setattr(
        news_service.openai_client, "responses", MagicMock(create=fake_create)
    )

    result = asyncio.run(news_service.generate_news_digest())

    assert result == "📋 notícias do dia"
    kwargs = fake_create.call_args.kwargs
    assert kwargs["model"] == config.NEWS_MODEL
    assert kwargs["instructions"] == config.NEWS_SYSTEM_PROMPT
    assert kwargs["tools"] == [{"type": "web_search"}]


def test_generate_news_digest_normalizes_double_star(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.output_text = "*Título*\n- **Bacen:** 140 vagas"
    fake_create = AsyncMock(return_value=fake_resp)
    monkeypatch.setattr(
        news_service.openai_client, "responses", MagicMock(create=fake_create)
    )
    result = asyncio.run(news_service.generate_news_digest())
    assert "**" not in result
    assert "*Bacen:*" in result


def test_generate_news_digest_none_on_empty(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.output_text = "   "
    fake_create = AsyncMock(return_value=fake_resp)
    monkeypatch.setattr(
        news_service.openai_client, "responses", MagicMock(create=fake_create)
    )
    assert asyncio.run(news_service.generate_news_digest()) is None


def test_generate_news_digest_none_on_exception(monkeypatch):
    fake_create = AsyncMock(side_effect=Exception("boom"))
    monkeypatch.setattr(
        news_service.openai_client, "responses", MagicMock(create=fake_create)
    )
    assert asyncio.run(news_service.generate_news_digest()) is None
