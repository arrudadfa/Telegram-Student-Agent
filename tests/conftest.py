"""Configura variáveis de ambiente falsas antes de importar o config nos testes.

config.py constrói um aiogram Bot (valida o formato do token) e o cliente OpenAI
na importação, e levanta ValueError se os tokens não existirem. Aqui definimos
valores falsos válidos e desabilitamos o Mercado Pago para o import ser limpo.
"""
import os

os.environ.setdefault(
    "TELEGRAM_BOT_TOKEN",
    "123456789:AAFakeTokenForLocalUnitTests_1234567890abcdef",
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
# String vazia => config trata como "não configurado" e não importa o mercadopago_service.
os.environ.setdefault("MERCADOPAGO_ACCESS_TOKEN", "")
