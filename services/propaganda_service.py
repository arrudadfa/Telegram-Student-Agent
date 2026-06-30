import asyncio
from datetime import datetime, timedelta

from config import bot, logger, VESTIBULARES_GROUP_ID, BRAZIL_TZ, ALLOWED_GROUP_IDS
from services.gpt_service import get_gpt_info_message
from services.news_service import generate_news_digest
from services.payment_service import payment_service

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


def _should_send_propaganda_to_chat(chat_id: int) -> bool:
    """Não envia propaganda em chat privado de quem já tem acesso ao bot."""
    if chat_id > 0 and payment_service.has_bot_access(chat_id):
        return False
    return True


class DailyBroadcastService:
    """Scheduler diário: envia o resumo de notícias todo dia no grupo vestibulares
    e, às sextas, propaganda do GPT Premium para chats permitidos (exceto pagantes)."""

    def __init__(self):
        self.last_sent_date = None

    def _should_send(self, today) -> bool:
        return self.last_sent_date != today

    async def _send_to_chat(self, chat_id: int, text: str) -> None:
        """Envia ao chat em pedaços; tenta Markdown e cai para texto puro se falhar."""
        chunks = split_message(text)
        for i, chunk in enumerate(chunks):
            try:
                await bot.send_message(
                    chat_id=chat_id, text=chunk, parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Markdown falhou ({e}); reenviando em texto puro")
                try:
                    await bot.send_message(chat_id=chat_id, text=chunk)
                except Exception as e2:
                    logger.error(f"Erro ao enviar ao chat {chat_id}: {e2}")
            if i < len(chunks) - 1:
                await asyncio.sleep(1)

    async def _send_friday_propaganda(self) -> None:
        propaganda = "📢 **Aproveite a promoção!** 📢\n\n" + get_gpt_info_message()
        sent_count = 0
        for chat_id in ALLOWED_GROUP_IDS:
            if not _should_send_propaganda_to_chat(chat_id):
                logger.info(f"Propaganda ignorada para usuário pagante {chat_id}")
                continue
            await self._send_to_chat(chat_id, propaganda)
            sent_count += 1
            await asyncio.sleep(1)
        logger.info(f"Propaganda de sexta enviada para {sent_count} chats")

    async def send_daily_broadcast(self, now: datetime | None = None) -> None:
        """Gera e envia o resumo do dia; às sextas envia propaganda para não pagantes."""
        now = now or datetime.now(BRAZIL_TZ)
        today = now.date()
        if not self._should_send(today):
            return

        digest = await generate_news_digest()
        if digest:
            await self._send_to_chat(VESTIBULARES_GROUP_ID, digest)
            logger.info("Resumo de notícias enviado ao grupo")
        else:
            logger.error("Resumo de notícias não gerado; envio do dia pulado")

        if now.weekday() == FRIDAY:
            await self._send_friday_propaganda()

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
