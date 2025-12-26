import asyncio
from datetime import datetime, timedelta
from config import bot, logger, ALLOWED_GROUP_IDS
from services.gpt_service import get_gpt_info_message

class PropagandaService:
    """
    Gerencia propagandas diárias sobre o serviço de correção de redação
    """
    def __init__(self):
        self.last_propaganda_date = None
        self.propaganda_sent_today = False
    
    def _should_send_propaganda(self) -> bool:
        """Verifica se deve enviar propaganda hoje"""
        today = datetime.now().date()
        if self.last_propaganda_date != today:
            return True
        return False
    
    async def send_daily_propaganda(self):
        """
        Envia propaganda diária para todos os grupos permitidos
        """
        if not self._should_send_propaganda():
            return
        
        propaganda_message = (
            "📢 **Aproveite a promoção!** 📢\n\n"
            + get_gpt_info_message()
        )
        
        sent_count = 0
        for group_id in ALLOWED_GROUP_IDS:
            try:
                await bot.send_message(
                    chat_id=group_id,
                    text=propaganda_message,
                    parse_mode='Markdown'
                )
                sent_count += 1
                logger.info(f"Propaganda enviada para grupo {group_id}")
                # Pequeno delay entre envios para evitar rate limit
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erro ao enviar propaganda para grupo {group_id}: {e}")
        
        self.last_propaganda_date = datetime.now().date()
        self.propaganda_sent_today = True
        logger.info(f"Propaganda diária enviada para {sent_count} grupos")
    
    async def start_daily_scheduler(self):
        """
        Inicia o scheduler para enviar propaganda diariamente às 9h
        """
        while True:
            now = datetime.now()
            # Calcula próximo horário de envio (9h da manhã)
            next_send = now.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Se já passou das 9h hoje, agenda para amanhã
            if now >= next_send:
                next_send += timedelta(days=1)
            
            # Calcula segundos até o próximo envio
            wait_seconds = (next_send - now).total_seconds()
            
            logger.info(f"Próxima propaganda agendada para {next_send.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Aguarda até o horário
            await asyncio.sleep(wait_seconds)
            
            # Envia propaganda
            await self.send_daily_propaganda()
            
            # Aguarda 1 segundo antes de recalcular
            await asyncio.sleep(1)

# Instância global do serviço
propaganda_service = PropagandaService()

