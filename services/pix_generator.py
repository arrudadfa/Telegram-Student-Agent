"""
Serviço para gerar códigos PIX dinâmicos via Mercado Pago API
"""
import json
from typing import Optional, Dict
from config import logger
from services.products_config import get_product
from services.gpt_service import GPT_Service_Price

# Valor padrão do pagamento (obtido do produto via gpt_service)
PAYMENT_AMOUNT = GPT_Service_Price

class PIXGenerator:
    """
    Gera códigos PIX dinâmicos via Mercado Pago API
    """
    
    def __init__(self, mapping_file: str = "data/pix_mappings.json"):
        self.mapping_file = mapping_file
        self.payment_to_user: dict = {}  # {payment_id: user_id}
        self.user_to_payment: dict = {}  # {user_id: payment_id}
        self._load_mappings()
    
    def _load_mappings(self):
        """Carrega mapeamentos de pagamentos para usuários"""
        try:
            import os
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.payment_to_user = data.get('payment_to_user', {})
                    self.user_to_payment = data.get('user_to_payment', {})
                logger.info(f"Carregados {len(self.payment_to_user)} mapeamentos de pagamento")
        except Exception as e:
            logger.error(f"Erro ao carregar mapeamentos: {e}")
            self.payment_to_user = {}
            self.user_to_payment = {}
    
    def _save_mappings(self):
        """Salva mapeamentos de pagamentos para usuários"""
        try:
            import os
            os.makedirs(os.path.dirname(self.mapping_file) if os.path.dirname(self.mapping_file) else ".", exist_ok=True)
            data = {
                'payment_to_user': self.payment_to_user,
                'user_to_payment': self.user_to_payment
            }
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar mapeamentos: {e}")
    
    async def generate_pix_for_user(self, user_id: int, amount: float = None, product_id: str = 'gpt_premium') -> Optional[Dict]:
        """
        Gera um código PIX via Mercado Pago API para um usuário
        
        Args:
            user_id: ID do usuário
            amount: Valor do pagamento (se None, usa o valor do produto)
            product_id: ID do produto (padrão: 'gpt_premium')
        
        Returns:
            Dicionário com payment_id, pix_code, qr_code_base64 ou None em caso de erro
        """
        from services.mercadopago_service import mercadopago_service
        
        # Se amount não fornecido, obtém do produto
        if amount is None:
            product = get_product(product_id)
            if product:
                amount = product.price
            else:
                amount = GPT_Service_Price
        
        if not mercadopago_service:
            logger.error("Mercado Pago não está configurado")
            return None
        
        # Verifica se já existe um pagamento pendente para este usuário
        if user_id in self.user_to_payment:
            payment_id = self.user_to_payment[user_id]
            # Verifica status do pagamento existente
            status = await mercadopago_service.check_payment_status(payment_id)
            if status == 'pending':
                # Reutiliza pagamento pendente
                payment_info = await mercadopago_service.get_payment_info(payment_id)
                if payment_info:
                    pix_code = mercadopago_service.extract_pix_code(payment_info)
                    qr_code_base64 = mercadopago_service.extract_pix_qr_code_base64(payment_info)
                    logger.info(f"Reutilizando pagamento PIX existente para usuário {user_id}")
                    return {
                        'payment_id': payment_id,
                        'pix_code': pix_code,
                        'qr_code_base64': qr_code_base64,
                        'status': status
                    }
        
        # Cria novo pagamento PIX
        product = get_product(product_id)
        description = f"{product.name if product else 'GPT Premium'} - Usuário {user_id}" if product else f"GPT Premium - Usuário {user_id}"
        payment_data = await mercadopago_service.create_pix_payment(user_id, amount, description)
        
        if not payment_data:
            logger.error(f"Erro ao criar pagamento PIX para usuário {user_id}")
            return None
        
        payment_id = str(payment_data.get('id'))
        pix_code = mercadopago_service.extract_pix_code(payment_data)
        qr_code_base64 = mercadopago_service.extract_pix_qr_code_base64(payment_data)
        status = payment_data.get('status')
        
        # Armazena o mapeamento
        self.payment_to_user[payment_id] = user_id
        self.user_to_payment[user_id] = payment_id
        
        # Salva os mapeamentos
        self._save_mappings()
        
        logger.info(f"Pagamento PIX criado para usuário {user_id}: {payment_id}")
        
        return {
            'payment_id': payment_id,
            'pix_code': pix_code,
            'qr_code_base64': qr_code_base64,
            'status': status
        }
    
    def get_user_by_payment_id(self, payment_id: str) -> Optional[int]:
        """
        Retorna o user_id associado a um payment_id
        """
        return self.payment_to_user.get(str(payment_id))
    
    def get_payment_id_by_user(self, user_id: int) -> Optional[str]:
        """
        Retorna o payment_id associado a um usuário
        """
        return self.user_to_payment.get(user_id)
    
    def clear_user_payment(self, user_id: int):
        """
        Remove o mapeamento de pagamento de um usuário (após pagamento confirmado)
        """
        if user_id in self.user_to_payment:
            payment_id = self.user_to_payment[user_id]
            del self.user_to_payment[user_id]
            if payment_id in self.payment_to_user:
                del self.payment_to_user[payment_id]
            self._save_mappings()
            logger.info(f"Mapeamento de pagamento removido para usuário {user_id}")

# Instância global do gerador
pix_generator = PIXGenerator()

