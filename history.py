from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Deque, Tuple

class ChatHistory:
    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.history: Dict[int, Deque[Tuple[str, datetime]]] = defaultdict(
            lambda: deque(maxlen=max_messages)
        )
    
    def add_message(self, user_id: int, message: str) -> None:
        """Adiciona uma mensagem ao histórico do usuário"""
        self.history[user_id].append((message, datetime.now()))
    
    def get_user_history(self, user_id: int) -> list[str]:
        """Retorna o histórico de mensagens do usuário"""
        return [msg[0] for msg in self.history[user_id]]
    
    def get_context_string(self, user_id: int) -> str:
        """Retorna o histórico formatado para uso como contexto"""
        messages = self.get_user_history(user_id)
        if not messages:
            return ""
        
        context = "Histórico recente da conversa:\n"
        for i, msg in enumerate(messages, 1):
            context += f"{i}. {msg}\n"
        return context

# Instância global do histórico
chat_history = ChatHistory() 