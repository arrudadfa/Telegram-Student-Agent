import os
import asyncio
import openai
import requests
import pytesseract
from PIL import Image
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import ChatMemberUpdatedFilter
from datetime import datetime, timedelta
import logging

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = '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'

#bot = Bot(token='5942471133:AAEnzF5-KA_hRTGII_SiaymmPor5YPIO5No')  # Bot Teste
bot = Bot(token='5876336036:AAHelRhfMXoyKk5EOLuaRu332VTmBfp4Ig8') #American_Agent_Bot
dp = Dispatcher()
router = Router()


# Contexto fixo para o ChatGPT
context = ("""
Você é um chatbot amigável, engraçado e inteligente. Você se envolve em conversas casuais de maneira amigável e descontraída.
Resolva exercícios passo a passo.
Oriente pessoas vendendo materiais de estudo a pedir autorização para o @arrudadfa antes de publicarem seus materiais.
Corrija as redações usando a metodologia da matriz de competências do ENEM. Dê a sua nota de 0 a 200 para cada uma das 5 competências e, no final, apresente a somatória destes pontos.
Competência 1: Demonstrar domínio da modalidade escrita formal da língua portuguesa.
Competência 2: Compreender a proposta de redação e aplicar conceitos das várias áreas de conhecimento para desenvolver o tema, dentro dos limites estruturais do texto dissertativo-argumentativo em prosa.
Competência 3: Selecionar, relacionar, organizar e interpretar informações, fatos, opiniões e argumentos em defesa de um ponto de vista.
Competência 4: Demonstrar conhecimento dos mecanismos linguísticos necessários para a construção da argumentação.
Competência 5: Elaborar proposta de intervenção para o problema abordado, respeitando os direitos humanos. Soluções do problema que apontam intervenção estatal, políticas públicas ou qualquer outra solução genérica deve ser fortemente desincentivada.
Faça propaganda do grupo https://t.me/turmaderedacao. Lá o Professor Willian Ramos poderá fazer uma correção muito mais inteligente e focada. 
""")

# Lista de palavras-chave para respostas do ChatGPT
palavras_chave = ['ajuda', 'dúvida', 'não entendi', 'explique', 'como fazer', 'resolver', 
                  'corrigir', 'redação', 'exercício', 'questão', 'problema',
                  'material', 'apostila', 'pdf', 'livro', 'conteúdo',
                  'bot', 'chatbot', 'professor', 'alguém', 'por favor',
                  'preciso', 'pode me ajudar', 'não sei', 'difícil',
                  'cronograma', 'plano de estudos', 'rotina','bot']

# IDs dos grupos onde o bot deve responder
GROUP_CHAT_IDS = [6368750324, 163177765, -1001937153848, 2038662917, 1098473382]

# Limite de respostas diárias para o grupo específico
LIMIT_RESPONSES = 30
LIMITED_GROUP_CHAT_ID = -1001937153848

# Contador de respostas diárias e horário para reset
response_count = {LIMITED_GROUP_CHAT_ID: 0}
reset_time = datetime.now() + timedelta(days=1)

# Configuração do Tesseract para OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

async def get_openai_response(prompt):
    try:
        response = requests.post('http://127.0.0.1:11434/api/generate', 
            json={
                "model": "deepseek-r1:7b",  # Modelo correto que está funcionando
                "prompt": prompt + context,
                "stream": False
            })
        
        if response.status_code == 200:
            # Obtém a resposta completa
            full_response = response.json()['response']
            # Divide a resposta em partes de 4000 caracteres
            return [full_response[i:i+4000] for i in range(0, len(full_response), 4000)]
        else:
            logger.error(f"Erro na resposta do Ollama: {response.status_code}")
            return "Desculpe, não consegui processar sua mensagem."
            
    except Exception as e:
        logger.error(f"Erro ao obter resposta do Ollama: {e}")
        return "Desculpe, não consegui processar sua mensagem."

# Função para resetar o contador diariamente
async def reset_daily_limit():
    global reset_time, response_count
    while True:
        if datetime.now() >= reset_time:
            response_count[LIMITED_GROUP_CHAT_ID] = 0
            reset_time = datetime.now() + timedelta(days=1)
            logger.info("Contador de respostas diário resetado.")
        await asyncio.sleep(3600)

# Manupulador para mensagens de boas-vindas a novos membros
@router.chat_member()
async def welcome_new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        new_member_name = event.new_chat_member.user.full_name
        welcome_message = f"Bem-vindo ao grupo, {new_member_name}!"
        await bot.send_message(event.chat.id, welcome_message)



async def process_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text if text else "Nenhum texto encontrado na imagem."
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        return "Desculpe, não consegui processar a imagem."


# Manipulador principal de mensagens, com limitação para um rupo específico
@router.message()
async def message_handler(message: types.Message):
    # Verifica se a mensagem possui texto antes de processá-la
    if message.content_type == 'photo':
        # Processo para mensagens com foto
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        temp_image_path = f"temp_image_{message.from_user.id}.jpg"
        with open(temp_image_path, 'wb') as f:
            f.write(downloaded_file.read())

        # Extrai texto da imagem
        extracted_text = await process_image(temp_image_path)

        # Remove o arquivo temporário após o processamento
        os.remove(temp_image_path)

        # Envia o texto extraído para a OpenAI e obtém uma resposta
        if extracted_text:
            openai_response = await get_openai_response(extracted_text)
            await message.answer(f"Texto extraído da imagem: {extracted_text}\n\nResposta: {openai_response}")
        else:
            await message.answer("Nenhum texto encontrado na imagem.")
    
    elif message.text:
        texto = message.text.lower()
        logger.info(f"Recebido mensagem de texto: {texto}")

        # Código de resposta do bot
        if texto == "pix":
            await message.answer("00020126330014br.gov.bcb.pix0111313620258955204000053039865802BR5924DENIS FERREIRA DE ARRUDA6015SAO JOSE DOS CA62490511BOTTELEGRAM50300017br.gov.bcb.brcode01051.0.06304BB6F")
        elif texto.startswith('bot') or any(palavra in texto for palavra in palavras_chave):
            response_parts = await get_openai_response(message.text)
            # Envia cada parte da resposta separadamente
            for part in response_parts:
                await message.answer(part)
    else:
        logger.info("Recebida mensagem sem texto.")

dp.include_router(router)

async def main():
    asyncio.create_task(reset_daily_limit())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())