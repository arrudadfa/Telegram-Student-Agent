import os
import asyncio
from openai import OpenAI
import pytesseract
from PIL import Image
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from datetime import datetime, timedelta
import logging

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciais
TELEGRAM_TOKEN = '7459837787:AAGbVqQsCJ6j8OOhDNVG1qCHYi7R-hHwWAU'
OPENAI_KEY = "sk-jzckD8WNBtje-0Q1ioRIn9QUqJWOwQ6uAi5vHhevj-T3BlbkFJ_FHHksO8lBA5qQlTlSwOs4nYJfsCj62pOu_vBwLC4A"

# Inicializa clientes
client = OpenAI(api_key=OPENAI_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()

# Lista de palavras-chave
palavras_chave = [
    'preciso de ajuda', 'alguém pode me ajudar', 'ajuda', 'resolver', 'cronograma',
    'estou vendendo', 'compartilho', 'alguém sabe dizer', 'como faço para',
    'alguém tem', 'bot', 'corrigir a minha redação', 'por favor'
]

# Prompt de sistema
context = """
Você é um chatbot amigável, engraçado e inteligente. Você se envolve em conversas casuais de maneira amigável e descontraída.
Resolva exercícios passo a passo.
Corrija as redações usando a metodologia da matriz de competências do ENEM. Dê a sua nota de 0 a 200 para cada uma das 5 competências e, no final, apresente a somatória destes pontos.
Competência 1: Demonstrar domínio da modalidade escrita formal da língua portuguesa.
Competência 2: Compreender a proposta de redação e aplicar conceitos das várias áreas de conhecimento para desenvolver o tema, dentro dos limites estruturais do texto dissertativo-argumentativo em prosa.
Competência 3: Selecionar, relacionar, organizar e interpretar informações, fatos, opiniões e argumentos em defesa de um ponto de vista.
Competência 4: Demonstrar conhecimento dos mecanismos linguísticos necessários para a construção da argumentação.
Competência 5: Elaborar proposta de intervenção para o problema abordado, respeitando os direitos humanos. Soluções do problema que apontam intervenção estatal, políticas públicas ou qualquer outra solução genérica deve ser fortemente desincentivada.
Verifique se o texto foi elaborado com base em algum template de redação já catalogado nos repositórios do ChatGPT. Em caso positivo, orientar o aluno a não utilizar templates prontos, mas sim exercitar cada vez mais a criatividade.
"""

# Função para obter resposta da OpenAI (nova API)
async def get_openai_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao obter resposta da OpenAI: {e}")
        return "Desculpe, não consegui processar sua mensagem."

# OCR - Extrai texto de imagem
async def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='por')
        return text.strip()
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        return ""

# Comando /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Bot iniciado. Envie um texto ou uma imagem contendo texto para correção ou análise.")

# Processa mensagens com foto (OCR)
@router.message(F.photo)
async def handle_photo(message: types.Message):
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_path = file_info.file_path
        downloaded_file = await bot.download_file(file_path)

        temp_image_path = f"temp_{message.from_user.id}.jpg"
        with open(temp_image_path, "wb") as f:
            f.write(downloaded_file.read())

        extracted_text = await extract_text_from_image(temp_image_path)
        os.remove(temp_image_path)

        if not extracted_text:
            await message.answer("Nenhum texto foi detectado na imagem.")
            return

        response = await get_openai_response(extracted_text)
        await message.answer(f"Texto extraído:\n\n{extracted_text}\n\nResposta:\n{response}")

    except Exception as e:
        logger.error(f"Erro ao lidar com imagem: {e}")
        await message.answer("Ocorreu um erro ao processar a imagem.")

# Processa mensagens de texto
@router.message()
async def message_handler(message: types.Message):
    if not message.text:
        logger.info("Mensagem sem texto ignorada.")
        return

    texto = message.text.lower()
    logger.info(f"Recebido texto: {texto}")

    if texto.startswith('bot') or any(p in texto for p in palavras_chave):
        response = await get_openai_response(message.text)
        await message.answer(response)

# Mensagens de boas-vindas
@router.chat_member()
async def welcome_new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        new_member_name = event.new_chat_member.user.full_name
        welcome_message = f"Bem-vindo ao grupo, {new_member_name}!"
        await bot.send_message(event.chat.id, welcome_message)

# Inicia o bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
