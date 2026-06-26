# Resumo diário de notícias + propaganda só às sextas — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O bot envia, todo dia às 9h (horário de Brasília), um resumo de notícias de concursos/vestibulares/praticagem gerado por busca web da OpenAI, e a propaganda do GPT Premium passa a ir somente às sextas — ambos apenas no grupo vestibulares.

**Architecture:** Um serviço novo `news_service.py` gera o texto do resumo via OpenAI Responses API com a ferramenta nativa `web_search`. O `propaganda_service.py` é reescrito como um scheduler/orquestrador diário que, no horário (fuso `America/Sao_Paulo`), pede o resumo e o envia ao grupo `-1001937153848`; às sextas envia também a propaganda. Constantes e o prompt ficam em `config.py`.

**Tech Stack:** Python 3.11+ (deploy), aiogram 3.x, openai 2.9.0 (Responses API), `zoneinfo` + `tzdata`, pytest.

## Global Constraints

- Grupo alvo (notícias e propaganda): `VESTIBULARES_GROUP_ID = -1001937153848` — exatamente esse, nenhum outro.
- Horário de envio: **09:00**, fuso `America/Sao_Paulo` (`BRAZIL_TZ`).
- Notícia: **todo dia**. Propaganda do GPT: **somente sexta** (`weekday() == 4`).
- Busca web: OpenAI Responses API, `openai_client.responses.create(..., tools=[{"type": "web_search"}])`, leitura via `response.output_text`.
- Limite de mensagem do Telegram: 4096 chars → enviar em pedaços de ≤ 4000.
- Envio tenta `parse_mode="Markdown"`; em erro, reenvia o mesmo pedaço sem `parse_mode`.
- Manter o nome do módulo `services/propaganda_service.py` e o objeto global `propaganda_service` (o `main.py` não muda de import).
- Falha na geração do resumo → logar e pular a notícia do dia (não enviar mensagem quebrada); a propaganda de sexta é independente.

---

### Task 1: Constantes de config, dependências e harness de testes

**Files:**
- Modify: `config.py` (adicionar imports e constantes)
- Modify: `requirements.txt` (adicionar `tzdata`)
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nada (primeira task).
- Produces:
  - `config.BRAZIL_TZ: zoneinfo.ZoneInfo` (`America/Sao_Paulo`)
  - `config.VESTIBULARES_GROUP_ID: int == -1001937153848`
  - `config.NEWS_MODEL: str` (modelo com suporte a web search)
  - `config.NEWS_SYSTEM_PROMPT: str` (instruções dos 3 temas, formato Telegram)
  - `tests/conftest.py` que define env vars falsas antes de importar `config`

- [ ] **Step 1: Criar `requirements-dev.txt`**

```
pytest>=8.0.0
```

- [ ] **Step 2: Adicionar `tzdata` ao `requirements.txt`**

Conteúdo final de `requirements.txt`:

```
aiogram>=3.0.0
openai>=2.0.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
Pillow>=10.0.0
tzdata>=2024.1
```

- [ ] **Step 3: Instalar dependências de teste**

Run: `python -m pip install -r requirements-dev.txt`
Expected: instala pytest sem erro.

- [ ] **Step 4: Criar `tests/conftest.py`** (env falsa para `import config` não falhar)

```python
"""Configura variáveis de ambiente falsas antes de importar o config nos testes.

config.py constrói um aiogram Bot (valida o formato do token) e o cliente OpenAI
na importação, e levanta ValueError se os tokens não existirem. Aqui definimos
valores falsos válidos e desabilitamos o Mercado Pago para o import ser limpo.
"""
import os

os.environ.setdefault(
    "TELEGRAM_BOT_TOKEN",
    "123456789:AAFakeTokenForLocalUnitTests_1234567890abcdef",
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
# String vazia => config trata como "não configurado" e não importa o mercadopago_service.
os.environ.setdefault("MERCADOPAGO_ACCESS_TOKEN", "")
```

- [ ] **Step 5: Escrever o teste que falha** em `tests/test_config.py`

```python
import config


def test_vestibulares_group_id():
    assert config.VESTIBULARES_GROUP_ID == -1001937153848


def test_brazil_timezone():
    assert str(config.BRAZIL_TZ) == "America/Sao_Paulo"


def test_news_model_is_str():
    assert isinstance(config.NEWS_MODEL, str) and config.NEWS_MODEL


def test_news_prompt_covers_three_themes():
    prompt = config.NEWS_SYSTEM_PROMPT
    assert "Concursos públicos federais" in prompt
    assert "Vestibulares" in prompt
    assert "Praticante de Prático" in prompt
    # Formatação Telegram: instrui a NÃO usar ### (headers que o Telegram não renderiza)
    assert "###" not in prompt
```

- [ ] **Step 6: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL com `AttributeError: module 'config' has no attribute 'VESTIBULARES_GROUP_ID'`.

- [ ] **Step 7: Adicionar o import de timezone no topo do `config.py`**

Logo após `import logging` (linha 4), adicionar:

```python
from zoneinfo import ZoneInfo
```

- [ ] **Step 8: Adicionar as constantes no `config.py`**

Logo após a linha `ALLOWED_GROUP_IDS = [...]` (linha ~40), adicionar:

```python
# Fuso horário oficial do bot (notícias e propaganda usam horário de Brasília)
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# Grupo t.me/vestibulareseconcursos — único destino do resumo diário e da propaganda
VESTIBULARES_GROUP_ID = -1001937153848

# Modelo usado para o resumo de notícias (precisa suportar a ferramenta web_search da
# Responses API). Se a conta não tiver acesso a este modelo, troque por "gpt-4.1".
NEWS_MODEL = "gpt-5.5"
```

- [ ] **Step 9: Adicionar `NEWS_SYSTEM_PROMPT` no `config.py`**

Após o bloco `CRONOGRAMA_SYSTEM_PROMPT = """..."""` (linha ~175), adicionar:

```python
# Prompt para o resumo diário de notícias (busca web). Formatação compatível com o
# Markdown legado do Telegram: negrito de UMA estrela (*Título*) e emojis nos títulos,
# sem usar ### (que o Telegram não renderiza).
NEWS_SYSTEM_PROMPT = """
Você é um assistente especializado em concursos públicos e vestibulares no Brasil. Sua tarefa é buscar e resumir as notícias mais recentes do dia sobre os seguintes temas:

1. Concursos públicos federais: novos editais abertos, inscrições encerradas, resultados publicados, datas de provas, vagas anunciadas por órgãos federais (Receita Federal, Banco Central, IBGE, Ministérios, autarquias federais, etc.).

2. Vestibulares: novidades sobre ENEM, FUVEST, UNICAMP, UEL, UFPR e outros vestibulares de universidades públicas e privadas — datas, gabaritos, resultados, convocações do SISU/PROUNI/FIES.

3. Concurso para Praticante de Prático: qualquer notícia, edital, resultado, convocação ou atualização sobre o concurso para praticante de prático (praticagem marítima no Brasil), incluindo editais de praticagem dos portos de Santos, Rio de Janeiro, Paranaguá, Itajaí, Salvador, Vitória, etc.

Instruções de execução:
- Use a busca na web para encontrar notícias recentes de hoje sobre cada um dos três temas.
- Faça buscas em português (ex.: "concursos públicos federais edital", "vestibular ENEM notícias", "concurso praticante de prático praticagem").
- Priorize fontes confiáveis: sites oficiais de órgãos públicos, Diário Oficial da União (DOU), QConcursos, Gran Cursos, Estratégia Concursos, G1, portais educacionais.
- Apresente as notícias organizadas por tema, em português, de forma clara e objetiva.
- Inclua datas, prazos e links quando disponíveis.
- Se não houver novidades relevantes em algum tema no dia, informe brevemente.

Formato de saída (use *negrito de uma estrela* nos títulos e NÃO use ###):

📋 *NOTÍCIAS DE CONCURSOS — [DATA DE HOJE]*

🏛️ *Concursos Públicos Federais*
[notícias e resumos]

🎓 *Vestibulares*
[notícias e resumos]

⚓ *Praticante de Prático*
[notícias e resumos]
"""
```

- [ ] **Step 10: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 testes).

- [ ] **Step 11: Commit**

```bash
git add config.py requirements.txt requirements-dev.txt tests/conftest.py tests/test_config.py
git commit -m "Add news/timezone config constants and test harness"
```

---

### Task 2: `news_service.py` — geração do resumo via web search

**Files:**
- Create: `services/news_service.py`
- Test: `tests/test_news_service.py`

**Interfaces:**
- Consumes: `config.openai_client`, `config.logger`, `config.NEWS_SYSTEM_PROMPT`, `config.NEWS_MODEL`, `config.BRAZIL_TZ`.
- Produces:
  - `build_news_input(today: datetime.date) -> str`
  - `async generate_news_digest() -> str | None`

- [ ] **Step 1: Escrever os testes que falham** em `tests/test_news_service.py`

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_news_service.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'services.news_service'`.

- [ ] **Step 3: Implementar `services/news_service.py`**

```python
"""Gera o resumo diário de notícias de concursos/vestibulares usando a
ferramenta nativa de busca web da OpenAI (Responses API). Este módulo só produz
texto — não conhece o Telegram."""

from datetime import date, datetime

from config import (
    openai_client,
    logger,
    NEWS_SYSTEM_PROMPT,
    NEWS_MODEL,
    BRAZIL_TZ,
)


def build_news_input(today: date) -> str:
    """Monta o texto de entrada (turno do usuário) com a data de hoje."""
    data_str = today.strftime("%d/%m/%Y")
    return (
        f"Busque na web e gere o resumo das notícias de hoje, {data_str}, "
        "sobre os três temas: Concursos Públicos Federais, Vestibulares e "
        "Concurso para Praticante de Prático. Siga o formato de saída definido."
    )


async def generate_news_digest() -> str | None:
    """Retorna o texto do resumo de notícias, ou None em caso de falha."""
    today = datetime.now(BRAZIL_TZ).date()
    try:
        response = await openai_client.responses.create(
            model=NEWS_MODEL,
            instructions=NEWS_SYSTEM_PROMPT,
            input=build_news_input(today),
            tools=[{"type": "web_search"}],
        )
        text = (response.output_text or "").strip()
        if not text:
            logger.error("Resumo de notícias retornou vazio da OpenAI")
            return None
        logger.info("Resumo de notícias gerado com sucesso")
        return text
    except Exception as e:
        logger.error(f"Erro ao gerar resumo de notícias: {e}", exc_info=True)
        return None
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/test_news_service.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add services/news_service.py tests/test_news_service.py
git commit -m "Add news_service: daily digest via OpenAI web search"
```

---

### Task 3: Reescrever `propaganda_service.py` como scheduler diário

**Files:**
- Modify (rewrite): `services/propaganda_service.py`
- Test: `tests/test_propaganda_service.py`

**Interfaces:**
- Consumes: `config.bot`, `config.logger`, `config.VESTIBULARES_GROUP_ID`, `config.BRAZIL_TZ`; `services.gpt_service.get_gpt_info_message`; `services.news_service.generate_news_digest`.
- Produces:
  - `split_message(text: str, limit: int = 4000) -> list[str]`
  - `next_run(now: datetime) -> datetime`
  - `class DailyBroadcastService` com:
    - `last_sent_date: date | None`
    - `_should_send(today: date) -> bool`
    - `async _send_to_group(text: str) -> None`
    - `async send_daily_broadcast(now: datetime | None = None) -> None`
    - `async start_daily_scheduler() -> None`
  - `propaganda_service = DailyBroadcastService()` (objeto global, nome preservado)

- [ ] **Step 1: Escrever os testes que falham** em `tests/test_propaganda_service.py`

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_propaganda_service.py -v`
Expected: FAIL (`AttributeError`/`TypeError` — `split_message`/`next_run`/assinatura ainda não existem).

- [ ] **Step 3: Reescrever `services/propaganda_service.py`**

Substituir TODO o conteúdo do arquivo por:

```python
import asyncio
from datetime import datetime, timedelta

from config import bot, logger, VESTIBULARES_GROUP_ID, BRAZIL_TZ
from services.gpt_service import get_gpt_info_message
from services.news_service import generate_news_digest

TELEGRAM_LIMIT = 4000  # margem segura abaixo do limite de 4096 do Telegram
SEND_HOUR = 9          # 09:00 horário de Brasília
FRIDAY = 4             # datetime.weekday(): segunda=0 ... sexta=4


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Quebra um texto em pedaços de até `limit` chars, preferindo fim de parágrafo."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if len(block) > limit:
            if current.strip():
                chunks.append(current.rstrip())
                current = ""
            for i in range(0, len(para), limit):
                chunks.append(para[i:i + limit])
            continue
        if len(current) + len(block) > limit:
            chunks.append(current.rstrip())
            current = block
        else:
            current += block
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


def next_run(now: datetime) -> datetime:
    """Próximo horário de envio (09:00 de hoje, ou de amanhã se já passou)."""
    target = now.replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


class DailyBroadcastService:
    """Scheduler diário: envia o resumo de notícias todo dia e, às sextas,
    também a propaganda do GPT Premium — sempre apenas no grupo vestibulares."""

    def __init__(self):
        self.last_sent_date = None

    def _should_send(self, today) -> bool:
        return self.last_sent_date != today

    async def _send_to_group(self, text: str) -> None:
        """Envia ao grupo em pedaços; tenta Markdown e cai para texto puro se falhar."""
        chunks = split_message(text)
        for i, chunk in enumerate(chunks):
            try:
                await bot.send_message(
                    chat_id=VESTIBULARES_GROUP_ID, text=chunk, parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Markdown falhou ({e}); reenviando em texto puro")
                try:
                    await bot.send_message(chat_id=VESTIBULARES_GROUP_ID, text=chunk)
                except Exception as e2:
                    logger.error(f"Erro ao enviar ao grupo {VESTIBULARES_GROUP_ID}: {e2}")
            if i < len(chunks) - 1:
                await asyncio.sleep(1)

    async def send_daily_broadcast(self, now: datetime | None = None) -> None:
        """Gera e envia o resumo do dia; às sextas envia também a propaganda."""
        now = now or datetime.now(BRAZIL_TZ)
        today = now.date()
        if not self._should_send(today):
            return

        digest = await generate_news_digest()
        if digest:
            await self._send_to_group(digest)
            logger.info("Resumo de notícias enviado ao grupo")
        else:
            logger.error("Resumo de notícias não gerado; envio do dia pulado")

        if now.weekday() == FRIDAY:
            propaganda = "📢 **Aproveite a promoção!** 📢\n\n" + get_gpt_info_message()
            await self._send_to_group(propaganda)
            logger.info("Propaganda de sexta enviada ao grupo")

        self.last_sent_date = today

    async def start_daily_scheduler(self) -> None:
        """Loop: dorme até o próximo 09:00 (Brasília) e dispara o envio do dia."""
        while True:
            now = datetime.now(BRAZIL_TZ)
            nxt = next_run(now)
            wait_seconds = (nxt - now).total_seconds()
            logger.info(
                f"Próximo envio diário agendado para "
                f"{nxt.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            await asyncio.sleep(wait_seconds)
            try:
                await self.send_daily_broadcast()
            except Exception as e:
                logger.error(f"Erro no envio diário: {e}", exc_info=True)
            await asyncio.sleep(1)


# Instância global do serviço (nome preservado para o main.py)
propaganda_service = DailyBroadcastService()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/test_propaganda_service.py -v`
Expected: PASS (11 testes).

- [ ] **Step 5: Commit**

```bash
git add services/propaganda_service.py tests/test_propaganda_service.py
git commit -m "Rewrite propaganda_service as daily news+Friday-ad scheduler"
```

---

### Task 4: Integração no `main.py` e verificação final

**Files:**
- Modify: `main.py` (apenas texto de log, sem mudança funcional)
- Test: suíte completa + verificação manual

**Interfaces:**
- Consumes: `propaganda_service.start_daily_scheduler` (inalterado).
- Produces: nenhuma nova API.

- [ ] **Step 1: Atualizar os logs do scheduler no `main.py`**

Em `main.py`, trocar as duas linhas de log de propaganda (linhas ~31 e ~33):

```python
        # Inicia o scheduler de envios diários (notícias + propaganda de sexta)
        logger.info("Iniciando scheduler de envios diários...")
        asyncio.create_task(propaganda_service.start_daily_scheduler())
        logger.info("Scheduler de envios diários iniciado")
```

- [ ] **Step 2: Rodar a suíte completa**

Run: `python -m pytest tests/ -v`
Expected: PASS (todos os testes das Tasks 1–3; 19 no total).

- [ ] **Step 3: Verificação manual da busca web (uma chamada real à OpenAI)**

Pré-requisito: `.env` com `OPENAI_API_KEY` real e `TELEGRAM_BOT_TOKEN` válido.
Criar `scripts/smoke_news.py` (arquivo temporário, NÃO commitar):

```python
import asyncio
from services.news_service import generate_news_digest

print(asyncio.run(generate_news_digest()))
```

Run: `python scripts/smoke_news.py`
Expected: imprime um resumo com as três seções (🏛️ / 🎓 / ⚓) e datas/links. Se der erro de modelo, ajustar `NEWS_MODEL` em `config.py` para `"gpt-4.1"` e repetir.
Ao terminar: `rm scripts/smoke_news.py`.

- [ ] **Step 4: Verificação manual do envio ao grupo (opcional, requer bot no grupo)**

Em um REPL com o bot rodando localmente, ou via script temporário não commitado:

```python
import asyncio
from services.propaganda_service import propaganda_service
from datetime import datetime
from config import BRAZIL_TZ

# força "agora" como uma sexta para testar notícia + propaganda
friday = datetime(2026, 6, 26, 9, 0, tzinfo=BRAZIL_TZ)
asyncio.run(propaganda_service.send_daily_broadcast(now=friday))
```

Expected: as mensagens aparecem no grupo `-1001937153848`. Confere se a formatação ficou legível (negrito/emoji) e, se necessário, ajusta o `NEWS_SYSTEM_PROMPT`.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "Update scheduler log messages for daily broadcast"
```

---

## Self-Review

**1. Spec coverage:**
- Propaganda só sexta, só grupo vestibulares → Task 3 (`weekday() == FRIDAY`, `VESTIBULARES_GROUP_ID`). ✓
- Resumo diário de notícias via busca web → Task 2 (`generate_news_digest` + `web_search`). ✓
- Prompt dos 3 temas → Task 1 (`NEWS_SYSTEM_PROMPT`). ✓
- Fuso `America/Sao_Paulo` → Task 1 (`BRAZIL_TZ`), usado em Task 2 e 3. ✓
- Limite/chunking + fallback de Markdown → Task 3 (`split_message`, `_send_to_group`). ✓
- Falha de busca pula o dia → Task 3 (`if digest: ... else: log`). ✓
- `tzdata` + nome de módulo preservado → Task 1 / Task 3. ✓
- Testes da lógica determinística → Tasks 1–3. ✓

**2. Placeholder scan:** Nenhum TBD/TODO; todo código está completo nos passos. ✓

**3. Type consistency:** `generate_news_digest() -> str | None` (Task 2) é consumido em Task 3 igual; `split_message`/`next_run`/`_send_to_group`/`send_daily_broadcast(now=...)` batem entre definição (Task 3) e testes. `VESTIBULARES_GROUP_ID`, `BRAZIL_TZ`, `NEWS_MODEL`, `NEWS_SYSTEM_PROMPT` (Task 1) usados com os mesmos nomes em Tasks 2–3. ✓
