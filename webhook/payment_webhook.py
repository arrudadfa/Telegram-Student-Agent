from aiohttp import web
import json
import hmac
import hashlib
from datetime import datetime
from config import logger
from services.payment_service import payment_service
from services.gpt_service import get_gpt_access_message, GPT_LINK

# Chave secreta para validar webhooks (configure no seu serviço de pagamento)
WEBHOOK_SECRET = "seu_secret_key_aqui"  # Altere para uma chave segura

async def handle_payment_webhook(request):
    """
    Handler para receber webhooks de pagamento via ngrok
    """
    try:
        # Lê o corpo da requisição
        data = await request.json()
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Valida a requisição (opcional, dependendo do serviço de pagamento)
        # if not validate_webhook_signature(request, data):
        #     return web.json_response({'error': 'Invalid signature'}, status=401)
        
        # Processa diferentes tipos de notificações do Mercado Pago
        event_type = data.get('type', data.get('action', data.get('event', '')))
        
        # Mercado Pago envia webhooks com 'payment' ou 'payment.updated' ou 'payment.created'
        if 'payment' in str(event_type).lower():
            # Extrai o payment_id do webhook
            payment_id = None
            payment_data_webhook = data.get('data', data)
            
            # Tenta extrair payment_id de diferentes formatos
            if isinstance(payment_data_webhook, dict):
                payment_id = payment_data_webhook.get('id')
            elif isinstance(payment_data_webhook, str):
                payment_id = payment_data_webhook
            else:
                payment_id = data.get('id')
            
            if not payment_id:
                logger.warning("Webhook recebido sem payment_id")
                return web.json_response({
                    'status': 'error',
                    'message': 'Payment ID not found'
                }, status=400)
            
            logger.info(f"Processando webhook para payment_id: {payment_id}")
            
            # Consulta a API do Mercado Pago para obter dados completos do pagamento
            from services.mercadopago_service import mercadopago_service
            if not mercadopago_service:
                logger.error("Mercado Pago não está configurado")
                return web.json_response({
                    'status': 'error',
                    'message': 'Mercado Pago not configured'
                }, status=500)
            
            # Obtém informações completas do pagamento
            payment_info = await mercadopago_service.get_payment_info(str(payment_id))
            if not payment_info:
                logger.error(f"Não foi possível obter informações do pagamento {payment_id}")
                return web.json_response({
                    'status': 'error',
                    'message': 'Could not fetch payment info'
                }, status=500)
            
            # Extrai informações do pagamento
            status = payment_info.get('status', '').lower()
            amount = float(payment_info.get('transaction_amount', 0))
            
            # Tenta identificar o user_id
            user_id = None
            
            # Opção 1: Identificar pelo payment_id através do mapeamento
            from services.pix_generator import pix_generator
            user_id = pix_generator.get_user_by_payment_id(str(payment_id))
            if user_id:
                logger.info(f"Usuário identificado pelo payment_id {payment_id}: {user_id}")
            
            # Opção 2: user_id no metadata (Mercado Pago envia aqui)
            if not user_id:
                metadata = payment_info.get('metadata', {})
                if metadata:
                    user_id = metadata.get('telegram_user_id') or metadata.get('user_id')
                    if user_id:
                        try:
                            user_id = int(user_id)
                        except:
                            user_id = None
            
            logger.info(f"Processando pagamento: user_id={user_id}, amount={amount}, status={status}")
            
            # Se não conseguiu identificar o usuário, retorna erro
            if not user_id:
                logger.warning(f"Não foi possível identificar usuário para payment_id {payment_id}")
                return web.json_response({
                    'status': 'error',
                    'message': 'User ID not found'
                }, status=400)
            
            # Processa diferentes status de pagamento
            if status == 'approved':
                # Pagamento aprovado - confirma o acesso
                pending = payment_service.get_pending_payment(user_id)
                product_id = pending.get('product_id', 'gpt_premium') if pending else 'gpt_premium'
                from services.products_config import get_product
                product = get_product(product_id)
                expected_amount = product.price if product else 50.0

                if amount < expected_amount:
                    logger.warning(f"Valor do pagamento insuficiente: {amount} < {expected_amount}")
                    return web.json_response({
                        'status': 'invalid',
                        'message': 'Insufficient payment amount'
                    }, status=400)
                
                if payment_service.confirm_payment_for_product(user_id, product_id):
                    try:
                        from config import bot
                        from services.bot_access_service import get_bot_access_granted_message

                        if product_id == 'bot_access':
                            access_message = get_bot_access_granted_message()
                        else:
                            access_message = get_gpt_access_message(product_id)
                        await bot.send_message(
                            chat_id=user_id,
                            text=access_message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Pagamento confirmado ({product_id}) para usuário {user_id}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem para usuário {user_id}: {e}")
                    
                    return web.json_response({
                        'status': 'success',
                        'message': 'Payment confirmed',
                        'user_id': user_id
                    })
                else:
                    logger.warning(f"Usuário {user_id} já tinha acesso confirmado")
                    return web.json_response({
                        'status': 'already_confirmed',
                        'message': 'User already has access'
                    })
            
            elif status == 'pending':
                # Pagamento ainda pendente - apenas registra
                logger.info(f"Pagamento {payment_id} ainda está pendente para usuário {user_id}")
                return web.json_response({
                    'status': 'pending',
                    'message': 'Payment is still pending'
                })
            
            elif status in ['rejected', 'cancelled', 'refunded']:
                # Pagamento rejeitado/cancelado
                logger.warning(f"Pagamento {payment_id} foi {status} para usuário {user_id}")
                return web.json_response({
                    'status': status,
                    'message': f'Payment was {status}'
                })
            
            else:
                # Status desconhecido
                logger.warning(f"Status de pagamento desconhecido: {status} para payment_id {payment_id}")
                return web.json_response({
                    'status': 'unknown',
                    'message': f'Unknown payment status: {status}'
                })
        
        # Outros tipos de eventos
        else:
            logger.info(f"Evento não processado: {event_type}")
            return web.json_response({
                'status': 'ignored',
                'message': f'Event type {event_type} not processed'
            })
    
    except json.JSONDecodeError:
        logger.error("Erro ao decodificar JSON do webhook")
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        return web.json_response({'error': str(e)}, status=500)

def validate_webhook_signature(request, data):
    """
    Valida a assinatura do webhook (implemente conforme seu provedor de pagamento)
    """
    # Exemplo para Mercado Pago:
    # signature = request.headers.get('x-signature')
    # if not signature:
    #     return False
    # expected_signature = hmac.new(
    #     WEBHOOK_SECRET.encode(),
    #     json.dumps(data).encode(),
    #     hashlib.sha256
    # ).hexdigest()
    # return hmac.compare_digest(signature, expected_signature)
    
    # Por enquanto, retorna True (desative em produção e implemente validação real)
    return True

async def health_check(request):
    """Endpoint de health check"""
    return web.json_response({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'payment_webhook'
    })

def create_webhook_app():
    """Cria a aplicação webhook"""
    app = web.Application()
    
    # Rota principal do webhook
    app.router.add_post('/webhook/payment', handle_payment_webhook)
    app.router.add_post('/payment', handle_payment_webhook)  # Rota alternativa
    
    # Health check
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    return app

