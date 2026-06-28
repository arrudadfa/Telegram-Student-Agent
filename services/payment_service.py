import json
import os
from typing import Set, Optional
from datetime import datetime
from config import logger, PAID_USERS_FILE, BOT_OWNER_ID

class PaymentService:
    """
    Gerencia pagamentos e acesso ao bot e ao GPT premium
    """
    def __init__(self, data_file: str = None):
        self.data_file = data_file or PAID_USERS_FILE
        self.paid_users: Set[int] = set()
        self.bot_access_users: Set[int] = set()
        self.pending_payments: dict = {}  # {user_id: {'timestamp': datetime, 'amount': float}}
        self._ensure_data_dir()
        self._load_data()
    
    def _ensure_data_dir(self):
        """Garante que o diretório de dados existe"""
        dir_path = os.path.dirname(self.data_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
    
    def _load_data(self):
        """Carrega dados de usuários pagantes do arquivo"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.paid_users = set(data.get('paid_users', []))
                    self.bot_access_users = set(data.get('bot_access_users', []))
                    # Converte timestamps de string para datetime
                    pending = data.get('pending_payments', {})
                    self.pending_payments = {
                        int(k): {
                            'timestamp': datetime.fromisoformat(v['timestamp']),
                            'amount': v['amount'],
                            **({k2: v2 for k2, v2 in v.items() if k2 not in ('timestamp', 'amount')})
                        }
                        for k, v in pending.items()
                    }
                logger.info(
                    f"Carregados {len(self.paid_users)} usuários GPT premium, "
                    f"{len(self.bot_access_users)} com acesso ao bot"
                )
        except Exception as e:
            logger.error(f"Erro ao carregar dados de pagamento: {e}")
            self.paid_users = set()
            self.bot_access_users = set()
            self.pending_payments = {}
    
    def _save_data(self):
        """Salva dados de usuários pagantes no arquivo"""
        try:
            data = {
                'paid_users': list(self.paid_users),
                'bot_access_users': list(self.bot_access_users),
                'pending_payments': {
                        str(k): {
                            'timestamp': v['timestamp'].isoformat(),
                            'amount': v['amount'],
                            **({k2: v2 for k2, v2 in v.items() if k2 not in ('timestamp', 'amount')})
                        }
                        for k, v in self.pending_payments.items()
                    }
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Dados de pagamento salvos: {len(self.paid_users)} GPT premium, "
                f"{len(self.bot_access_users)} acesso ao bot"
            )
        except Exception as e:
            logger.error(f"Erro ao salvar dados de pagamento: {e}")
    
    def is_paid_user(self, user_id: int) -> bool:
        """Verifica se o usuário já pagou pelo GPT premium"""
        return user_id in self.paid_users

    def has_bot_access(self, user_id: int) -> bool:
        """Verifica se o usuário pode conversar com o bot"""
        if user_id == BOT_OWNER_ID:
            return True
        if user_id in self.bot_access_users:
            return True
        if user_id in self.paid_users:
            return True
        return False

    def confirm_bot_access(self, user_id: int) -> bool:
        """Confirma pagamento de acesso ao bot. Retorna False se já tinha acesso."""
        if user_id in self.bot_access_users or user_id in self.paid_users:
            return False

        self.bot_access_users.add(user_id)
        if user_id in self.pending_payments:
            del self.pending_payments[user_id]

        from services.pix_generator import pix_generator
        pix_generator.clear_user_payment(user_id)

        self._save_data()
        logger.info(f"Acesso ao bot confirmado para usuário {user_id}")
        return True

    def grant_bot_access(self, user_id: int) -> bool:
        """Libera acesso manualmente (admin). Retorna False se já tinha acesso."""
        if user_id in self.bot_access_users or user_id in self.paid_users:
            return False

        self.bot_access_users.add(user_id)
        self._save_data()
        logger.info(f"Acesso ao bot concedido manualmente para usuário {user_id}")
        return True

    def confirm_payment_for_product(self, user_id: int, product_id: str) -> bool:
        """Confirma pagamento conforme o produto adquirido."""
        if product_id == 'bot_access':
            return self.confirm_bot_access(user_id)
        return self.confirm_payment(user_id)
    
    def register_pending_payment(self, user_id: int, amount: float = None, payment_reference: str = None, pix_code: str = None, product_id: str = 'gpt_premium'):
        """Registra um pagamento pendente"""
        from services.products_config import get_product
        
        # Se amount não fornecido, obtém do produto
        if amount is None:
            product = get_product(product_id)
            amount = product.price if product else 50.0
        
        self.pending_payments[user_id] = {
            'timestamp': datetime.now(),
            'amount': amount,
            'payment_reference': payment_reference,
            'pix_code': pix_code,
            'product_id': product_id
        }
        self._save_data()
        logger.info(f"Pagamento pendente registrado para usuário {user_id}: R$ {amount}, PIX: {pix_code[:50] if pix_code else 'N/A'}...")
    
    def confirm_payment(self, user_id: int, payment_id: str = None) -> bool:
        """
        Confirma um pagamento e concede acesso ao GPT
        Retorna True se o pagamento foi confirmado, False se já estava pago
        """
        if user_id in self.paid_users:
            return False
        
        self.paid_users.add(user_id)
        if user_id in self.pending_payments:
            del self.pending_payments[user_id]
        
        # Remove mapeamento de pagamento
        from services.pix_generator import pix_generator
        pix_generator.clear_user_payment(user_id)
        
        self._save_data()
        logger.info(f"Pagamento confirmado para usuário {user_id}")
        return True
    
    def get_pending_payment(self, user_id: int) -> Optional[dict]:
        """Retorna informações sobre pagamento pendente do usuário"""
        return self.pending_payments.get(user_id)
    
    def get_user_by_payment_id(self, payment_id: str) -> Optional[int]:
        """
        Retorna o user_id associado a um payment_id do Mercado Pago
        """
        from services.pix_generator import pix_generator
        return pix_generator.get_user_by_payment_id(payment_id)
    
    def check_payment_by_pix_key(self, pix_key: str, amount: float = None, product_id: str = 'gpt_premium') -> bool:
        """
        Verifica se um pagamento foi realizado através da chave PIX
        NOTA: Esta é uma implementação básica. Em produção, você precisaria:
        - Integrar com API de pagamento (Mercado Pago, PagSeguro, etc.)
        - Usar webhook para receber notificações de pagamento
        - Verificar extrato bancário via API
        
        Por enquanto, retorna False. Esta função deve ser implementada
        com a integração real de pagamento.
        """
        from services.products_config import get_product
        
        # Se amount não fornecido, obtém do produto
        if amount is None:
            product = get_product(product_id)
            amount = product.price if product else 50.0
        
        # TODO: Implementar verificação real de pagamento PIX
        # Exemplo de integração futura:
        # - Usar API do banco para verificar transações
        # - Usar serviço de pagamento como Mercado Pago
        # - Verificar webhook de notificação
        # - Usar serviços como Gerencianet, Asaas, etc.
        return False
    
    async def verify_payment_for_user(self, user_id: int) -> bool:
        """
        Verifica se há pagamento pendente e tenta confirmar consultando o Mercado Pago
        Retorna True se o pagamento foi confirmado, False caso contrário
        """
        if self.has_bot_access(user_id):
            return True
        
        # Verifica pagamento pendente
        pending = self.get_pending_payment(user_id)
        if not pending:
            return False
        
        # Obtém o payment_id do usuário
        from services.pix_generator import pix_generator
        payment_id = pix_generator.get_payment_id_by_user(user_id)
        
        if not payment_id:
            logger.warning(f"Não foi possível encontrar payment_id para usuário {user_id}")
            return False
        
        # Consulta o Mercado Pago para verificar o status do pagamento
        from services.mercadopago_service import mercadopago_service
        if not mercadopago_service:
            logger.error("Mercado Pago não está configurado")
            return False
        
        try:
            payment_info = await mercadopago_service.get_payment_info(str(payment_id))
            if not payment_info:
                return False

            status = payment_info.get('status', '').lower()
            amount = float(payment_info.get('transaction_amount', 0))
            logger.info(f"Status do pagamento {payment_id} para usuário {user_id}: {status}")
            
            # Se o pagamento foi aprovado, confirma
            if status == 'approved':
                product_id = pending.get('product_id', 'gpt_premium')
                from services.products_config import get_product
                product = get_product(product_id)
                expected_amount = product.price if product else 50.0

                if amount < expected_amount:
                    logger.warning(f"Valor do pagamento insuficiente: {amount} < {expected_amount}")
                    return False

                if self.confirm_payment_for_product(user_id, product_id):
                    logger.info(f"Pagamento confirmado automaticamente para usuário {user_id} ({product_id})")
                    return True
                else:
                    logger.warning(f"Falha ao confirmar pagamento para usuário {user_id}")
                    return False
            
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento no Mercado Pago para usuário {user_id}: {e}")
            return False
    

# Instância global do serviço
payment_service = PaymentService()

