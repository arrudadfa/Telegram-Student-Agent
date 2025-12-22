import os
from dotenv import load_dotenv
import logging
from aiogram import Bot, Dispatcher, Router
import openai

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tokens diretos (temporário, até resolver o .env)
TELEGRAM_BOT_TOKEN = 'BOT-TOKEN-AQUI'
OPENAI_API_KEY = 'API-KEY-AQUI'

# Configuração OpenAI
openai.api_key = OPENAI_API_KEY

# Configuração Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Verificação de token
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Token do Telegram não encontrado! Verifique o arquivo .env")

# IDs dos grupos permitidos
ALLOWED_GROUP_IDS = [6368750324, 163177765, -1001937153848, 2038662917, 1098473382,163177765]

# Limites
MAX_DAILY_RESPONSES = 30
LIMITED_GROUP_ID = -1001937153848

# Palavras-chave para trigger do bot
TRIGGER_KEYWORDS = [
    'preciso de ajuda', 'ajuda', 'resolver', 'cronograma',
    'corrigir a minha redação', 'bot', 'oi bot', 'olá bot',
    'alguém pode me ajudar', 'como faço para', 'alguém tem',
    'por favor', 'material', 'materiais', 'exercício', 'dúvida',
    'questão', 'problema', 'explicar'
]

# Configuração do Sistema OpenAI
SYSTEM_PROMPT = """
Você é um chatbot amigável, engraçado e inteligente. 
Você se envolve em conversas casuais de maneira amigável e descontraída.
Resolva exercícios passo a passo.
Oriente pessoas vendendo materiais de estudo a pedir autorização para o @arrudadfa antes de publicarem seus materiais.
Corrija as redações usando a metodologia da matriz de competências do ENEM. 
Dê a sua nota de 0 a 200 para cada uma das 5 competências e, no final, apresente a somatória destes pontos.

Competência 1: Demonstrar domínio da modalidade escrita formal da língua portuguesa.
Competência 2: Compreender a proposta de redação e aplicar conceitos das várias áreas de conhecimento para desenvolver o tema.
Competência 3: Selecionar, relacionar, organizar e interpretar informações, fatos, opiniões e argumentos em defesa de um ponto de vista.
Competência 4: Demonstrar conhecimento dos mecanismos linguísticos necessários para a construção da argumentação.
Competência 5: Elaborar proposta de intervenção para o problema abordado, respeitando os direitos humanos.

Faça propaganda do grupo https://t.me/turmaderedacao para correções de redação.
"""

# Adicione após a definição dos tokens
logger.info(f"Token do Telegram carregado: {TELEGRAM_BOT_TOKEN[:10]}...")
logger.info(f"Token da OpenAI carregado: {OPENAI_API_KEY[:10]}...") 