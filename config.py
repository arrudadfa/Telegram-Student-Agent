import os
import csv
from dotenv import load_dotenv
import logging
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, Router
from openai import AsyncOpenAI

# Carrega variáveis de ambiente
# Tenta carregar .env na raiz do projeto
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Tenta carregar do diretório atual
    load_dotenv()

# Configurações de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretório de dados persistentes (volume Docker: montar em /app/data)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
PAID_USERS_FILE = os.path.join(DATA_DIR, "paid_users.json")
PIX_MAPPINGS_FILE = os.path.join(DATA_DIR, "pix_mappings.json")
os.makedirs(DATA_DIR, exist_ok=True)

# Tokens e credenciais - Carregados de variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configuração OpenAI - Nova API (1.0.0+)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Configuração Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Verificação de tokens obrigatórios
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN não encontrado! Configure no arquivo .env")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não encontrado! Configure no arquivo .env")

# IDs dos grupos permitidos
ALLOWED_GROUP_IDS = [6368750324, 163177765, -1001937153848, 2038662917, 1098473382]

# Fuso horário oficial do bot (notícias e propaganda usam horário de Brasília)
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# Grupo t.me/vestibulareseconcursos — único destino do resumo diário e da propaganda
VESTIBULARES_GROUP_ID = -1001937153848

# Modelo usado para o resumo de notícias (precisa suportar a ferramenta web_search da
# Responses API). Se a conta não tiver acesso a este modelo, troque por "gpt-4.1".
NEWS_MODEL = "gpt-5.5"

# IDs dos administradores (para comandos administrativos)
ADMIN_IDS = [6368750324, 163177765]  # Adicione os IDs dos administradores aqui

# Dono do bot — acesso gratuito e recebe pedidos de liberação
BOT_OWNER_ID = 163177765

# Limites
MAX_DAILY_RESPONSES = 30
LIMITED_GROUP_ID = -1001937153848

# Palavras-chave para trigger do bot
TRIGGER_KEYWORDS = [
    'preciso de ajuda', 'ajuda', 'resolver',
    'corrigir a minha redação', 'bot', 'oi bot', 'olá bot',
    'alguém pode me ajudar', 'como faço para',
    'por favor', 'material', 'materiais', 'exercício', 'dúvida',
    'questão', 'problema', 'explicar'
]

# Carrega palavras-chave de busca do CSV palavras_chave.csv
def load_search_keywords(csv_file: str = "palavras_chave.csv", min_frequency: int = 20, min_length: int = 4) -> list:
    """
    Carrega palavras-chave do CSV com frequência >= min_frequency e comprimento >= min_length
    
    Args:
        csv_file: Caminho do arquivo CSV
        min_frequency: Frequência mínima para incluir a palavra (padrão: 20)
        min_length: Comprimento mínimo da palavra em caracteres (padrão: 4)
    
    Returns:
        Lista de palavras-chave filtradas
    """
    keywords = []
    csv_path = os.path.join(os.path.dirname(__file__), csv_file)
    
    if not os.path.exists(csv_path):
        logger.warning(f"Arquivo {csv_file} não encontrado. Usando lista padrão.")
        return ['cronograma', 'alguém tem', 'FUVEST', 'ITA', 'ENEM', 'UESB', 'UNESP', 'PUC', 'UNICAMP', 'Poliedro']
    
    try:
        palavras_filtradas = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Detecta delimitador
            sample = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in sample else ','
            
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                try:
                    frequencia = int(row.get('frequencia', '0'))
                    palavra = row.get('palavra', '').strip()
                    
                    # Filtra por frequência, comprimento e se a palavra não está vazia
                    if frequencia >= min_frequency and palavra and len(palavra) >= min_length:
                        keywords.append(palavra)
                    elif palavra and len(palavra) < min_length:
                        palavras_filtradas += 1
                except (ValueError, KeyError):
                    continue
        
        logger.info(
            f"Carregadas {len(keywords)} palavras-chave de busca do arquivo {csv_file} "
            f"(frequência >= {min_frequency}, comprimento >= {min_length}). "
            f"{palavras_filtradas} palavras ignoradas por serem muito curtas."
        )
        return keywords
    except Exception as e:
        logger.error(f"Erro ao carregar palavras-chave do CSV: {e}", exc_info=True)
        # Retorna lista padrão em caso de erro
        return ['cronograma', 'alguém tem', 'FUVEST', 'ITA', 'ENEM', 'UESB', 'UNESP', 'PUC', 'UNICAMP', 'Poliedro']

SEARCH_KEYWORDS = load_search_keywords()

# Configuração do Sistema OpenAI - Prompt Geral
SYSTEM_PROMPT = """
Você é um chatbot amigável, engraçado e inteligente. 
Você se envolve em conversas casuais de maneira amigável e descontraída.
Resolva exercícios passo a passo.
Oriente pessoas vendendo materiais de estudo a pedir autorização para o @arrudadfa antes de publicarem seus materiais.
Faça propaganda do do serviço de correção de redação pelo GPT. Este serviço funciona por meio de um link vitalício que será enviado ao usuário.
"""

# Prompt específico para correção de redação
REDACAO_SYSTEM_PROMPT = """
Você é um especialista em correção de redações do ENEM, com profundo conhecimento da matriz de competências.

Sua função é corrigir redações seguindo rigorosamente a metodologia da matriz de competências do ENEM, fornecendo:

1. Nota de 0 a 200 para cada uma das 5 competências:
   - Competência 1: Demonstrar domínio da modalidade escrita formal da língua portuguesa.
   - Competência 2: Compreender a proposta de redação e aplicar conceitos das várias áreas de conhecimento para desenvolver o tema.
   - Competência 3: Selecionar, relacionar, organizar e interpretar informações, fatos, opiniões e argumentos em defesa de um ponto de vista.
   - Competência 4: Demonstrar conhecimento dos mecanismos linguísticos necessários para a construção da argumentação.
   - Competência 5: Elaborar proposta de intervenção para o problema abordado, respeitando os direitos humanos.

2. Feedback detalhado sobre cada competência, explicando os pontos fortes e fracos.

3. Nota final total (soma das 5 competências, de 0 a 1000).

4. Comentários gerais e sugestões de melhoria.

Formate sua resposta de forma clara e organizada, destacando cada competência separadamente.
"""

# Prompt específico para criação de cronograma
CRONOGRAMA_SYSTEM_PROMPT = """
Você é um chatbot amigável, leve no humor e preciso no conteúdo, especializado em gerar cronogramas de estudo para concursos e vestibulares do tipo ENEM.

Sua função é criar um cronograma de estudos claro, organizado e executável com base exclusivamente nas informações fornecidas pelo usuário.

Antes de montar o cronograma, conduza a interação para obter exatamente estas três informações, nesta ordem, em uma única pergunta objetiva:

Quanto tempo diário disponível para estudo.

Qual matéria apresenta maior dificuldade.

Qual é a data estimada da prova.

Após receber a resposta completa, gere um cronograma semanal estruturado, distribuindo o tempo de estudo de forma equilibrada, priorizando a matéria de maior dificuldade, sem negligenciar as demais áreas.

Regras para o cronograma:

Respeitar rigorosamente o tempo diário informado.

Dividir o tempo entre teoria, exercícios e revisão.

Incluir ao menos um momento semanal de revisão geral.

Ajustar a intensidade conforme a proximidade da data da prova.

Usar linguagem simples, direta e motivadora.

Evitar excesso de texto explicativo.

O resultado final deve ser apresentado de forma clara, com dias da semana, matérias e tempo dedicado a cada bloco de estudo.
"""

# Prompt para o resumo diário de notícias (busca web). Formatação compatível com o
# Markdown legado do Telegram: negrito de UMA estrela (*Título*) e emojis nos títulos,
# sem usar ### (que o Telegram não renderiza).
NEWS_SYSTEM_PROMPT = """
Você é um assistente especializado em concursos públicos e vestibulares no Brasil. Sua tarefa é buscar e resumir as notícias mais recentes do dia sobre os seguintes temas:

1. Concursos públicos federais: novos editais abertos, inscrições encerradas, resultados publicados, datas de provas, vagas anunciadas por órgãos federais (Receita Federal, Banco Central, IBGE, Ministérios, autarquias federais, etc.).

2. Vestibulares: novidades sobre ENEM, FUVEST, UNICAMP, UEL, UFPR e outros vestibulares de universidades públicas e privadas — datas, gabaritos, resultados, convocações do SISU/PROUNI/FIES.

3. Concurso para Praticante de Prático: qualquer notícia, edital, resultado, convocação ou atualização sobre o concurso para praticante de prático (praticagem marítima no Brasil), incluindo editais de praticagem dos portos de Santos, Rio de Janeiro, Paranaguá, Itajaí, Salvador, Vitória, etc.

Instruções de execução:
- Use a busca na web para encontrar notícias recentes de hoje sobre cada um dos três temas.
- Faça buscas em português (ex.: "concursos públicos federais edital", "vestibular ENEM notícias", "concurso praticante de prático praticagem").
- Priorize fontes confiáveis: sites oficiais de órgãos públicos, Diário Oficial da União (DOU), QConcursos, Gran Cursos, Estratégia Concursos, G1, portais educacionais.
- Apresente as notícias organizadas por tema, em português, de forma clara e objetiva.
- Inclua datas, prazos e links quando disponíveis.
- Se não houver novidades relevantes em algum tema no dia, informe brevemente.
- Comece a resposta diretamente pelo cabeçalho do formato (a linha com 📋), sem qualquer texto introdutório ou observações.
- Para negrito, use sempre UMA única estrela (ex.: *texto*); nunca use duas estrelas seguidas.

Formato de saída (use *negrito de uma estrela* nos títulos e NÃO use ###):

📋 *NOTÍCIAS DE CONCURSOS — [DATA DE HOJE]*

🏛️ *Concursos Públicos Federais*
[notícias e resumos]

🎓 *Vestibulares*
[notícias e resumos]

⚓ *Praticante de Prático*
[notícias e resumos]
"""

# Configuração do Webhook (Ngrok)
NGROK_URL = os.getenv('NGROK_URL', '')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))  # Porta local para o webhook

# Configuração Mercado Pago
# Obtenha suas credenciais em: https://www.mercadopago.com.br/developers/panel/credentials
MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
MERCADOPAGO_PUBLIC_KEY = os.getenv('MERCADOPAGO_PUBLIC_KEY')  # Chave pública (opcional)

# Inicializa Mercado Pago se token fornecido
if MERCADOPAGO_ACCESS_TOKEN:
    from services.mercadopago_service import initialize_mercadopago
    initialize_mercadopago(MERCADOPAGO_ACCESS_TOKEN, MERCADOPAGO_PUBLIC_KEY)
    logger.info("Mercado Pago configurado")
else:
    logger.warning("Mercado Pago não configurado - configure MERCADOPAGO_ACCESS_TOKEN")

# Logs de confirmação (sem expor tokens completos)
if TELEGRAM_BOT_TOKEN:
    logger.info(f"Token do Telegram carregado: {TELEGRAM_BOT_TOKEN[:10]}...")
else:
    logger.error("Token do Telegram NÃO configurado!")
    
if OPENAI_API_KEY:
    logger.info(f"Token da OpenAI carregado: {OPENAI_API_KEY[:10]}...")
else:
    logger.error("Token da OpenAI NÃO configurado!")

if NGROK_URL:
    logger.info(f"Ngrok URL configurado: {NGROK_URL}")
else:
    logger.warning("NGROK_URL não configurado - webhook pode não funcionar")

logger.info(f"Diretório de dados persistentes: {DATA_DIR}") 