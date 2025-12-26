import json
import csv
import os

# --- CONFIGURAÇÕES ---
ARQUIVO_INPUT = 'result.json'        # Seu arquivo do Telegram
ARQUIVO_OUTPUT = 'arquivos_limpos.csv'
CANAL_URL = 'vestibulareseconcursos' # Para gerar o link (opcional, mas útil)

def gerar_csv_limpo():
    # 1. Carregar o JSON
    if not os.path.exists(ARQUIVO_INPUT):
        print(f"Erro: {ARQUIVO_INPUT} não encontrado.")
        return

    print("📖 Lendo arquivo JSON...")
    with open(ARQUIVO_INPUT, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ajuste para pegar a lista correta
    msgs = data.get('messages', []) if isinstance(data, dict) else data
    
    # 2. Preparar o CSV
    print(f"⚙️ Processando e filtrando PDFs...")
    
    with open(ARQUIVO_OUTPUT, 'w', newline='', encoding='utf-8') as csvfile:
        # Definindo as colunas
        fieldnames = ['id', 'file_name', 'link_completo']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        
        writer.writeheader()
        
        count = 0
        for msg in msgs:
            # FILTROS:
            # 1. Tem que ser mensagem
            # 2. Tem que ser PDF
            # 3. ID tem que ser positivo (indexável)
            if (msg.get('type') == 'message' and 
                msg.get('mime_type') == 'application/pdf' and
                msg.get('id', -1) > 0):
                
                msg_id = msg['id']
                file_name = msg.get('file_name', 'Sem Nome')
                
                # Gera o link útil para você testar
                link = f"https://t.me/{CANAL_URL}/{msg_id}"
                
                # Escreve a linha
                writer.writerow({
                    'id': msg_id,
                    'file_name': file_name,
                    'link_completo': link
                })
                count += 1

    print(f"✅ Concluído! {count} arquivos PDF exportados para '{ARQUIVO_OUTPUT}'.")

if __name__ == "__main__":
    gerar_csv_limpo()