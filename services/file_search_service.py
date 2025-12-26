"""
Serviço para buscar arquivos no CSV arquivos_limpos.csv
"""
import csv
import os
import random
from typing import List, Optional, Dict
from config import logger

# Caminho do CSV relativo à raiz do projeto
CSV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "arquivos_limpos.csv")

class FileSearchService:
    """
    Serviço para buscar arquivos no CSV
    """
    
    def __init__(self, csv_file: str = CSV_FILE):
        self.csv_file = csv_file
        self._cache = None
        self._cache_loaded = False
    
    def _load_csv(self) -> List[Dict[str, str]]:
        """
        Carrega o CSV em memória (com cache)
        """
        if self._cache_loaded and self._cache is not None:
            return self._cache
        
        if not os.path.exists(self.csv_file):
            logger.warning(f"Arquivo CSV não encontrado: {self.csv_file}")
            return []
        
        try:
            files = []
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                # Tenta detectar o delimitador
                sample = f.read(1024)
                f.seek(0)
                delimiter = ';' if ';' in sample else ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    # Normaliza os nomes das colunas (remove espaços)
                    normalized_row = {k.strip(): v.strip() if isinstance(v, str) else v 
                                    for k, v in row.items()}
                    files.append(normalized_row)
            
            self._cache = files
            self._cache_loaded = True
            logger.info(f"Carregados {len(files)} arquivos do CSV")
            return files
        except Exception as e:
            logger.error(f"Erro ao carregar CSV: {e}", exc_info=True)
            return []
    
    def search_files(self, search_term: str, limit: int = 4) -> List[Dict[str, str]]:
        """
        Busca arquivos no CSV pelo termo de busca
        
        Args:
            search_term: Termo para buscar em file_name
            limit: Número máximo de resultados (padrão: 4)
            
        Returns:
            Lista de arquivos encontrados (máximo 'limit' itens)
        """
        if not search_term:
            return []
        
        files = self._load_csv()
        if not files:
            return []
        
        search_term_lower = search_term.lower()
        matches = []
        
        # Busca arquivos que contenham o termo no file_name
        for file_info in files:
            file_name = file_info.get('file_name', '').lower()
            if search_term_lower in file_name:
                matches.append(file_info)
        
        # Se houver múltiplos resultados, seleciona aleatoriamente até 'limit'
        if len(matches) > limit:
            selected = random.sample(matches, limit)
            logger.info(f"Encontrados {len(matches)} arquivos para '{search_term}', selecionados {limit} aleatoriamente")
            return selected
        
        logger.info(f"Encontrados {len(matches)} arquivo(s) para '{search_term}'")
        return matches
    
    def search_files_multiple_terms(self, search_terms: List[str], limit: int = 4) -> List[Dict[str, str]]:
        """
        Busca arquivos no CSV por múltiplos termos de busca
        
        Args:
            search_terms: Lista de termos para buscar em file_name
            limit: Número máximo de resultados (padrão: 4)
            
        Returns:
            Lista de arquivos encontrados (máximo 'limit' itens), combinando resultados de todos os termos
        """
        if not search_terms:
            return []
        
        all_matches = []
        seen_ids = set()  # Para evitar duplicatas
        
        # Busca por cada termo
        for search_term in search_terms:
            if not search_term:
                continue
            
            matches = self.search_files(search_term, limit=limit * 2)  # Busca mais para ter opções
            
            # Adiciona apenas arquivos únicos (por ID)
            for match in matches:
                file_id = match.get('id')
                if file_id and file_id not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(file_id)
        
        # Se houver mais resultados que o limite, seleciona aleatoriamente
        if len(all_matches) > limit:
            selected = random.sample(all_matches, limit)
            logger.info(f"Encontrados {len(all_matches)} arquivos únicos para termos '{search_terms}', selecionados {limit} aleatoriamente")
            return selected
        
        logger.info(f"Encontrados {len(all_matches)} arquivo(s) único(s) para termos '{search_terms}'")
        return all_matches
    
    def clear_cache(self):
        """
        Limpa o cache (útil se o CSV for atualizado)
        """
        self._cache = None
        self._cache_loaded = False

# Instância global do serviço
file_search_service = FileSearchService()

