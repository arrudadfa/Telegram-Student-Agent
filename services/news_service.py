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


def _to_telegram_markdown(text: str) -> str:
    """Normaliza o negrito para o Markdown legado do Telegram, que usa UMA estrela.
    O modelo às vezes devolve **negrito** (duas estrelas), que o Telegram não renderiza."""
    return text.replace("**", "*")


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
        text = _to_telegram_markdown((response.output_text or "").strip())
        if not text:
            logger.error("Resumo de notícias retornou vazio da OpenAI")
            return None
        logger.info("Resumo de notícias gerado com sucesso")
        return text
    except Exception as e:
        logger.error(f"Erro ao gerar resumo de notícias: {e}", exc_info=True)
        return None
