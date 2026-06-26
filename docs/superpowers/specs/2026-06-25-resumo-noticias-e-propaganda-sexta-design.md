# Design: Resumo diário de notícias (busca web) + propaganda do GPT só às sextas

**Data:** 2026-06-25
**Status:** Aprovado para implementação

## 1. Contexto e problema

Hoje o bot (`services/propaganda_service.py`) roda um scheduler que, **todo dia às 9h**, envia a
**propaganda do GPT Premium** para **todos** os grupos em `ALLOWED_GROUP_IDS`. O horário é calculado
com `datetime.now()`, ou seja, depende do fuso do servidor (há `Dockerfile`, então o deploy
provavelmente roda em UTC — "9h" e "sexta-feira" sairiam deslocados em 3h).

O bot é 100% OpenAI (`gpt-4` via `chat.completions`) e **não tem acesso à internet**.

### Objetivos

1. A propaganda do GPT Premium passa a ser enviada **somente às sextas-feiras** e **somente** no
   grupo `t.me/vestibulareseconcursos` (ID `-1001937153848`).
2. O bot passa a enviar, **todo dia às 9h (horário de Brasília)**, um **resumo de notícias** sobre
   concursos públicos federais, vestibulares e o concurso de Praticante de Prático, gerado por meio
   de **busca inteligente na internet**, seguindo o prompt definido na Seção 7.
3. Corrigir o cálculo de horário/dia-da-semana para usar explicitamente o fuso `America/Sao_Paulo`.

### Não-objetivos (YAGNI)

- Não enviar notícias para os demais grupos (decisão: só o grupo vestibulares).
- Não criar painel/admin para configurar temas ou horário (constantes no `config.py` bastam).
- Não trocar o provedor do resto do bot (correção de redação etc. continuam no OpenAI atual).

## 2. Decisões tomadas

| Tema | Decisão |
|---|---|
| Mecanismo de busca web | **OpenAI Responses API** com a ferramenta nativa de busca web (reaproveita `OPENAI_API_KEY`, sem novo provedor) |
| Destino do resumo diário | **Somente** o grupo vestibulares `-1001937153848` |
| Identificação do grupo | ID numérico `-1001937153848` (confirmado pelo usuário; já é o `LIMITED_GROUP_ID`) |
| Horário | **09h, horário de Brasília** (`America/Sao_Paulo`) |
| Frequência da notícia | **Todo dia**, incluindo fins de semana |
| Ordem às sextas | Notícia primeiro, propaganda do GPT depois |
| Nome do módulo | Mantém `propaganda_service.py` e o objeto global `propaganda_service` (minimiza churn de imports) |

## 3. Arquitetura / componentes

### 3.1 `services/news_service.py` (novo)

Responsabilidade única: **gerar o texto do resumo de notícias**. Não conhece o Telegram.

- `async def generate_news_digest() -> str | None`
  - Injeta a data de hoje (Brasília) no prompt.
  - Chama `openai_client.responses.create(...)` com a ferramenta de busca web habilitada.
  - Retorna o texto formatado (Telegram-friendly) ou `None` em caso de falha.
- Constante de prompt: usa `NEWS_SYSTEM_PROMPT` do `config.py` (Seção 7).
- Tratamento de erro: captura exceções, registra com `logger.error(...)` e retorna `None`.

> **A confirmar na implementação** (contra a doc oficial da OpenAI, via context7):
> - nome exato do tipo do tool (`web_search` vs `web_search_preview`);
> - modelo com suporte a busca web na Responses API (ex.: família GPT-5 / `gpt-4.1`);
> - formato de leitura da resposta (`response.output_text`).

### 3.2 `services/propaganda_service.py` (reescrito)

Vira o **orquestrador/scheduler diário**. Mantém a classe com o objeto global `propaganda_service`
e o método `start_daily_scheduler()` (chamado pelo `main.py`).

- `_now()` → `datetime.now(BRAZIL_TZ)`.
- `_next_run(now)` → próximo 09:00 Brasília (hoje se ainda não passou, senão amanhã).
- `_should_send(today)` → evita envio duplicado no mesmo dia (compara com `last_sent_date`).
- `async def send_daily_broadcast()`:
  1. Se já enviou hoje, retorna.
  2. Gera notícia via `news_service.generate_news_digest()`.
     - Se veio texto, envia ao grupo (com chunking + fallback de Markdown — Seção 4).
     - Se `None`, registra no log e segue (não envia mensagem quebrada).
  3. Se hoje (Brasília) for **sexta** (`weekday() == 4`): envia a propaganda do GPT
     (`gpt_service.get_gpt_info_message()`) ao grupo.
  4. Marca `last_sent_date = hoje`.
- `async def start_daily_scheduler()`: loop que dorme até `_next_run` e chama `send_daily_broadcast()`.
- Helper de envio `_send_to_group(text)`: faz chunking (≤ 4096) e tenta `parse_mode='Markdown'`,
  com fallback para texto puro se o Telegram rejeitar.

### 3.3 `config.py` (acréscimos)

- `from zoneinfo import ZoneInfo` e `BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")`.
- `VESTIBULARES_GROUP_ID = -1001937153848` (alvo das notícias e da propaganda).
- `NEWS_SYSTEM_PROMPT = """..."""` (Seção 7), seguindo o padrão dos prompts já existentes
  (`SYSTEM_PROMPT`, `REDACAO_SYSTEM_PROMPT`, `CRONOGRAMA_SYSTEM_PROMPT`).

### 3.4 `requirements.txt`

- Adicionar `tzdata` (necessário para `zoneinfo` em Windows e imagens de container slim).

## 4. Formatação e robustez de envio

- **Limite do Telegram (4096 chars):** `_send_to_group` quebra o texto em pedaços de até ~4000
  caracteres (preferindo quebrar em fim de parágrafo) antes de enviar.
- **Markdown frágil:** texto gerado por IA pode ter `*`/`_` desbalanceado e quebrar
  `parse_mode='Markdown'`. Estratégia: tenta enviar com Markdown; em `TelegramBadRequest`
  (ou erro equivalente), reenvia o mesmo pedaço **sem** `parse_mode`.
- **Prompt Telegram-friendly:** o `NEWS_SYSTEM_PROMPT` instrui o modelo a usar negrito de uma
  estrela (`*Título*`) e emojis nos títulos de seção, **evitando** `###` (que o Markdown legado do
  Telegram não renderiza).
- **Delay anti rate-limit:** mantém `await asyncio.sleep(1)` entre envios de pedaços.

## 5. Fluxo do scheduler (pseudocódigo)

```
start_daily_scheduler():
  while True:
    now  = datetime.now(BRAZIL_TZ)
    nxt  = _next_run(now)                      # hoje 09:00 ou amanhã 09:00
    sleep((nxt - now).total_seconds())
    send_daily_broadcast()
    sleep(1)

send_daily_broadcast():
  hoje = datetime.now(BRAZIL_TZ).date()
  if hoje == last_sent_date: return
  texto = news_service.generate_news_digest()
  if texto: _send_to_group(texto)
  else:     logger.error("Resumo de notícias não gerado; envio do dia pulado")
  if datetime.now(BRAZIL_TZ).weekday() == 4:   # sexta
    _send_to_group("📢 *Aproveite a promoção!* 📢\n\n" + get_gpt_info_message())
  last_sent_date = hoje
```

## 6. Tratamento de erros

| Falha | Comportamento |
|---|---|
| Busca/OpenAI falha | `generate_news_digest()` retorna `None`; scheduler loga e pula a notícia do dia |
| Telegram rejeita Markdown | Reenvia o pedaço sem `parse_mode` |
| Erro ao enviar ao grupo | `logger.error(...)`; não derruba o loop do scheduler |
| Exceção inesperada no loop | Capturada/logada; o loop continua (não encerra o bot) |

## 7. Prompt de notícias (`NEWS_SYSTEM_PROMPT`)

Você é um assistente especializado em concursos públicos e vestibulares no Brasil. Sua tarefa é
buscar e resumir as notícias mais recentes do dia sobre os seguintes temas:

1. **Concursos públicos federais**: novos editais abertos, inscrições encerradas, resultados
   publicados, datas de provas, vagas anunciadas por órgãos federais (Receita Federal, Banco
   Central, IBGE, Ministérios, autarquias federais, etc.).
2. **Vestibulares**: novidades sobre ENEM, FUVEST, UNICAMP, UEL, UFPR e outros vestibulares de
   universidades públicas e privadas — datas, gabaritos, resultados, convocações do
   SISU/PROUNI/FIES.
3. **Concurso para Praticante de Prático**: qualquer notícia, edital, resultado, convocação ou
   atualização sobre o concurso para praticante de prático (praticagem marítima no Brasil),
   incluindo editais de praticagem dos portos de Santos, Rio de Janeiro, Paranaguá, Itajaí,
   Salvador, Vitória, etc.

Instruções de execução:
- Use a busca web para encontrar notícias recentes de hoje sobre cada um dos três temas.
- Faça buscas em português (ex.: "concursos públicos federais edital", "vestibular ENEM notícias",
  "concurso praticante de prático praticagem").
- Priorize fontes confiáveis: sites oficiais de órgãos públicos, Diário Oficial da União (DOU),
  QConcursos, Gran Cursos, Estratégia Concursos, G1, portais educacionais.
- Apresente as notícias organizadas por tema, em português, de forma clara e objetiva.
- Inclua datas, prazos e links quando disponíveis.
- Se não houver novidades relevantes em algum tema no dia, informe brevemente.

Formatação (compatível com Telegram): use negrito de **uma** estrela para títulos (`*Título*`),
emojis nos títulos de seção e **não** use `###`. Estrutura de saída:

```
📋 *NOTÍCIAS DE CONCURSOS — [DATA DE HOJE]*

🏛️ *Concursos Públicos Federais*
[notícias e resumos]

🎓 *Vestibulares*
[notícias e resumos]

⚓ *Praticante de Prático*
[notícias e resumos]
```

## 8. Plano de testes

Repositório não tem suíte hoje. Adicionar testes unitários (sem rede) para a lógica determinística:

- `_next_run`: dado um "agora", retorna 09:00 do dia certo (hoje vs. amanhã), no fuso correto.
- Detecção de sexta-feira via `weekday()` no fuso `America/Sao_Paulo`.
- `_should_send`: não reenvia no mesmo dia.
- Chunking de mensagens longas (> 4096) em pedaços válidos.
- `generate_news_digest`: montagem do prompt e leitura da resposta com o cliente OpenAI **mockado**.

Envio real ao Telegram e busca web real ficam em verificação manual.

## 9. Mudanças de arquivos (resumo)

| Arquivo | Mudança |
|---|---|
| `services/news_service.py` | **novo** — geração do resumo via Responses API + busca web |
| `services/propaganda_service.py` | **reescrito** — orquestrador/scheduler diário (notícia + propaganda de sexta), com fuso, chunking e fallback de Markdown |
| `config.py` | `BRAZIL_TZ`, `VESTIBULARES_GROUP_ID`, `NEWS_SYSTEM_PROMPT` |
| `requirements.txt` | `+ tzdata` |
| `main.py` | sem mudança funcional (continua chamando `propaganda_service.start_daily_scheduler()`); ajustar log se necessário |
| `tests/` | **novo** — testes unitários da lógica determinística |
