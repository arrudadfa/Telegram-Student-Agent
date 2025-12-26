from datetime import datetime, timedelta
from typing import Dict
from config import logger

class DailyLimitService:
    """
    Gerencia limites diários de correções por usuário
    """
    def __init__(self):
        # Dicionário: {user_id: {'count': int, 'last_reset': datetime}}
        self.user_limits: Dict[int, Dict] = {}
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _should_reset(self) -> bool:
        """Verifica se é necessário resetar os contadores (meia-noite)"""
        now = datetime.now()
        if now.date() > self.reset_time.date():
            return True
        return False
    
    def _reset_all_limits(self):
        """Reseta todos os contadores diários"""
        self.user_limits.clear()
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info("Contadores diários resetados")
    
    def can_make_correction(self, user_id: int) -> bool:
        """
        Verifica se o usuário pode fazer uma correção hoje
        Returns: True se pode, False se já atingiu o limite
        """
        # Reseta contadores se necessário
        if self._should_reset():
            self._reset_all_limits()
        
        # Se o usuário não está no dicionário, pode fazer correção
        if user_id not in self.user_limits:
            return True
        
        # Verifica se o último reset foi hoje
        user_data = self.user_limits[user_id]
        if user_data['last_reset'].date() < datetime.now().date():
            # Reset do usuário específico
            self.user_limits[user_id] = {'count': 0, 'last_reset': datetime.now()}
            return True
        
        # Verifica se já atingiu o limite (1 correção por dia)
        return user_data['count'] < 1
    
    def register_correction(self, user_id: int):
        """
        Registra uma correção feita pelo usuário
        """
        if self._should_reset():
            self._reset_all_limits()
        
        if user_id not in self.user_limits:
            self.user_limits[user_id] = {'count': 0, 'last_reset': datetime.now()}
        
        self.user_limits[user_id]['count'] += 1
        self.user_limits[user_id]['last_reset'] = datetime.now()
        logger.info(f"Correção registrada para usuário {user_id}. Total hoje: {self.user_limits[user_id]['count']}")
    
    def get_remaining_corrections(self, user_id: int) -> int:
        """
        Retorna quantas correções o usuário ainda pode fazer hoje
        """
        if self.can_make_correction(user_id):
            return 1 - self.user_limits.get(user_id, {}).get('count', 0)
        return 0

# Instância global do serviço
daily_limit_service = DailyLimitService()

