import csv
import re
from collections import Counter
import os

# --- CONFIGURAÇÕES ---
ARQUIVO_INPUT = 'arquivos_limpos.csv'
ARQUIVO_OUTPUT = 'palavras_chave.csv'

# Palavras que queremos ignorar (Stopwords)
STOPWORDS = {
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma', 'os', 'no', 
    'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'ao', 'ele', 'das', 'pdf', 'arquivo',
}

def limpar_e_tokenizar(texto):
    """
    Recebe um texto (nome do arquivo), remove extensão, pontuação e números,
    e devolve uma lista de palavras úteis.
    """
    # 1. Remove a extensão .pdf
    texto = texto.lower().replace('.pdf', '')
    
    # 2. Usa Regex para pegar apenas palavras (letras, incluindo acentos)
    # Ignora números e símbolos especiais
    palavras = re.findall(r'[a-záàâãéèêíïóôõöúçñ]+', texto)
    
    # 3. Filtra stopwords e palavras com menos de 2 letras
    palavras_uteis = [p for p in palavras if p not in STOPWORDS and len(p) > 2]
    
    return palavras_uteis

def gerar_contador():
    if not os.path.exists(ARQUIVO_INPUT):
        print(f"Erro: {ARQUIVO_INPUT} não encontrado.")
        return

    print("📊 Lendo CSV e contando palavras...")
    
    contador_geral = Counter()

    try:
        with open(ARQUIVO_INPUT, 'r', encoding='utf-8') as f:
            # Detecta se o CSV usa ';' ou ',' (o script anterior usava ';')
            leitor = csv.DictReader(f, delimiter=';')
            
            for linha in leitor:
                nome_arquivo = linha.get('file_name', '')
                palavras = limpar_e_tokenizar(nome_arquivo)
                contador_geral.update(palavras)
                
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return

    # --- SALVAR RESULTADO ---
    print(f"💾 Salvando contagem em {ARQUIVO_OUTPUT}...")
    
    with open(ARQUIVO_OUTPUT, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out, delimiter=';')
        
        # Cabeçalho solicitado: Frequência (número) e Palavra
        writer.writerow(['frequencia', 'palavra'])
        
        # Escreve as palavras ordenadas da mais comum para a menos comum
        for palavra, frequencia in contador_geral.most_common():
            writer.writerow([frequencia, palavra])

    print(f"✅ Sucesso! {len(contador_geral)} palavras únicas catalogadas.")
    
    # Mostra um top 10 no terminal para conferência
    print("\n🏆 Top 10 Palavras mais frequentes:")
    for palavra, freq in contador_geral.most_common(10):
        print(f"{freq}: {palavra}")

if __name__ == "__main__":
    gerar_contador()