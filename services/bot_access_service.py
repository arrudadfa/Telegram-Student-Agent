"""
Mensagens e utilitários para o paywall de acesso ao bot (R$ 10).
"""

from typing import Optional

from services.products_config import get_product

BOT_ACCESS_PRODUCT_ID = 'bot_access'


PITCH_MESSAGE = (
    "Olá! Eu sou o Student_agent. Estou aqui para te ajudar a passar em um vestibular "
    "ou em um concurso público. Minha infraestrutura precisa de suporte e para continuarmos "
    "nosso plano preciso de um suporte. A quantia de 10 reais ja me ajuda muito. Isso também "
    "cria um compromisso de uso e de estudo. Meu desenvolvedor trabalha todos os dias neste "
    "projeto ajudando pessoas a ter o mesmo sucesso que ele.\n"
    "Quer chegar lá também?"
)


def get_pitch_message() -> str:
    return PITCH_MESSAGE


def get_paywall_message() -> str:
    product = get_product(BOT_ACCESS_PRODUCT_ID)
    price = product.price if product else 10.0
    return (
        "🔒 **Acesso ao bot**\n\n"
        f"Para conversar comigo, é necessário pagar **R$ {price:.2f}** (pagamento único via PIX).\n\n"
        "💳 Use o botão **Pagamentos** ou digite /acesso para gerar o PIX e liberar o uso.\n"
        "📩 Ou digite /liberacao para pedir liberação gratuita ao @arrudadfa.\n\n"
        "🤖 Com o acesso você pode:\n"
        "• Corrigir redações\n"
        "• Buscar materiais de estudo\n"
        "• Criar cronogramas\n"
        "• Tirar dúvidas e resolver exercícios"
    )


def get_bot_access_granted_message() -> str:
    return (
        "🎉 **Pagamento confirmado!** 🎉\n\n"
        "✅ Seu acesso ao bot foi liberado!\n\n"
        "Agora você pode usar todos os recursos:\n"
        "• ✍️ /redação — correção de redação\n"
        "• 🔍 /arquivo — busca de materiais\n"
        "• 📅 /cronograma — cronograma personalizado\n"
        "• 💬 Envie dúvidas e exercícios normalmente\n\n"
        "Digite /start para ver o menu."
    )


def get_access_request_sent_message() -> str:
    return (
        "📩 **Pedido enviado!**\n\n"
        "Seu pedido de liberação foi encaminhado ao @arrudadfa.\n"
        "Aguarde a resposta — você será avisado aqui quando o acesso for liberado."
    )


def get_access_request_notification(user_id: int, full_name: str, username: Optional[str]) -> str:
    username_display = f"@{username}" if username else "sem username"
    return (
        "📩 **Pedido de liberação de acesso**\n\n"
        f"👤 Nome: {full_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📱 Username: {username_display}\n\n"
        f"Para liberar: /liberar {user_id}"
    )


def get_access_granted_by_admin_message() -> str:
    return (
        "✅ **Acesso liberado!**\n\n"
        "O @arrudadfa liberou seu acesso ao bot gratuitamente.\n"
        "Digite /start para começar."
    )
