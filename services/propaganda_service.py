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
