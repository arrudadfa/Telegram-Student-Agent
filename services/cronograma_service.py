from datetime import datetime, timedelta
from typing import List, Dict

class CronogramaService:
    @staticmethod
    def criar_cronograma(materias: List[str], horas_disponiveis: int) -> Dict:
        """Cria um cronograma de estudos baseado nas matérias e tempo disponível"""
        cronograma = {
            "segunda": [],
            "terca": [],
            "quarta": [],
            "quinta": [],
            "sexta": [],
            "sabado": [],
            "domingo": []
        }
        
        # Lógica para distribuir as matérias
        # ...
        
        return cronograma 