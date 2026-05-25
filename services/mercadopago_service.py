"""
Serviço de integração com Mercado Pago para gerar PIX e verificar pagamentos
"""
import aiohttp
import json
from typing import Optional, Dict
from datetime import datetime
from config import logger, NGROK_URL

class MercadoPagoService:
    """
    Gerencia pagamentos via Mercado Pago API
    """
    
    def __init__(self, access_token: str, public_key: str = None):
        """
        Inicializa o serviço do Mercado Pago
        
        Args:
            access_token: Token de acesso do Mercado Pago (obtenha em https://www.mercadopago.com.br/developers)
            public_key: Chave pública (opcional, para pagamentos no frontend)
        """
        self.access_token = access_token
        self.public_key = public_key
        self.base_url = "https://api.mercadopago.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_pix_payment(self, user_id: int, amount: float = 50.0, description: str = None) -> Optional[Dict]:
        """
        Cria um pagamento PIX via Mercado Pago
        
        Args:
            user_id: ID do usuário do Telegram
            amount: Valor do pagamento
            description: Descrição do pagamento
            
        Returns:
            Dicionário com informações do pagamento, incluindo código PIX e QR code
        """
        if not description:
            description = f"GPT Premium - Usuário {user_id}"
        
        notification_url = None
        if NGROK_URL:
            base_url = NGROK_URL.rstrip('/')
            notification_url = f"{base_url}/webhook/payment"

        # Dados do pagamento
        payment_data = {
            "transaction_amount": amount,
            "description": description,
            "payment_method_id": "pix",
            "payer": {
                "email": f"user_{user_id}@telegram.bot"  # Email fictício baseado no user_id
            },
            "metadata": {
                "user_id": str(user_id),
                "telegram_user_id": user_id,
                "service": "gpt_premium"
            }
        }

        if notification_url:
            payment_data["notification_url"] = notification_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/payments",
                    headers=self.headers,
                    json=payment_data
                ) as response:
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"Pagamento PIX criado para usuário {user_id}: {data.get('id')}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Erro ao criar pagamento PIX: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Erro ao criar pagamento PIX: {e}")
            return None
    
    async def get_payment_info(self, payment_id: str) -> Optional[Dict]:
        """
        Obtém informações de um pagamento
        
        Args:
            payment_id: ID do pagamento no Mercado Pago
            
        Returns:
            Dicionário com informações do pagamento
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v1/payments/{payment_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Erro ao obter pagamento {payment_id}: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Erro ao obter pagamento: {e}")
            return None
    
    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Verifica o status de um pagamento
        
        Args:
            payment_id: ID do pagamento
            
        Returns:
            Status do pagamento (approved, pending, rejected, etc.)
        """
        payment_info = await self.get_payment_info(payment_id)
        if payment_info:
            return payment_info.get('status')
        return None
    
    def extract_pix_code(self, payment_data: Dict) -> Optional[str]:
        """
        Extrai o código PIX (copia e cola) dos dados do pagamento
        
        Args:
            payment_data: Dados do pagamento retornados pela API
            
        Returns:
            Código PIX ou None
        """
        # O código PIX geralmente está em point_of_interaction.transaction_data.qr_code
        point_of_interaction = payment_data.get('point_of_interaction', {})
        transaction_data = point_of_interaction.get('transaction_data', {})
        qr_code = transaction_data.get('qr_code')
        qr_code_base64 = transaction_data.get('qr_code_base64')
        
        # Retorna o código PIX (qr_code é o código copia e cola)
        return qr_code
    
    def extract_pix_qr_code_base64(self, payment_data: Dict) -> Optional[str]:
        """
        Extrai o QR Code em base64 para exibição
        
        Args:
            payment_data: Dados do pagamento retornados pela API
            
        Returns:
            QR Code em base64 ou None
        """
        point_of_interaction = payment_data.get('point_of_interaction', {})
        transaction_data = point_of_interaction.get('transaction_data', {})
        return transaction_data.get('qr_code_base64')
    
    def get_user_id_from_payment(self, payment_data: Dict) -> Optional[int]:
        """
        Extrai o user_id dos metadados do pagamento
        
        Args:
            payment_data: Dados do pagamento retornados pela API
            
        Returns:
            user_id ou None
        """
        metadata = payment_data.get('metadata', {})
        user_id = metadata.get('telegram_user_id') or metadata.get('user_id')
        if user_id:
            try:
                return int(user_id)
            except:
                return None
        return None

# Instância global (será inicializada no config.py)
mercadopago_service: Optional[MercadoPagoService] = None

def initialize_mercadopago(access_token: str, public_key: str = None):
    """
    Inicializa o serviço do Mercado Pago
    """
    global mercadopago_service
    mercadopago_service = MercadoPagoService(access_token, public_key)
    logger.info("Serviço Mercado Pago inicializado")

