import asyncio
from aiohttp import web
from config import bot, dp, logger, WEBHOOK_PORT, NGROK_URL
from handlers.message_handlers import router
from services.propaganda_service import propaganda_service
from webhook.payment_webhook import create_webhook_app

async def start_webhook_server():
    """Inicia o servidor webhook em background"""
    app = create_webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    logger.info(f"Servidor webhook iniciado na porta {WEBHOOK_PORT}")
    logger.info(f"Webhook URL: {NGROK_URL}/webhook/payment")
    logger.info(f"Health check: {NGROK_URL}/health")

async def main():
    try:
        # Registra os handlers
        logger.info("Registrando handlers...")
        dp.include_router(router)
        logger.info("Handlers registrados com sucesso")
        
        # Inicia o servidor webhook em background
        logger.info("Iniciando servidor webhook...")
        asyncio.create_task(start_webhook_server())
        
        # Inicia o scheduler de propagandas diárias em background
        logger.info("Iniciando scheduler de propagandas...")
        asyncio.create_task(propaganda_service.start_daily_scheduler())
        logger.info("Scheduler de propagandas diárias iniciado")
        
        # Verifica se o bot está configurado corretamente
        logger.info("Verificando configuração do bot...")
        bot_info = await bot.get_me()
        logger.info(f"Bot conectado: @{bot_info.username} ({bot_info.first_name})")
        
        logger.info("Iniciando polling...")
        await dp.start_polling(bot, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao iniciar bot: {e}", exc_info=True)
    finally:
        logger.info("Encerrando bot...")
        await bot.session.close()
        logger.info("Bot encerrado")

if __name__ == '__main__':
    asyncio.run(main()) 