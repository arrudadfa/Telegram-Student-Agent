"""
Serviço para gerenciar informações sobre o GPT premium
"""

from services.products_config import get_product

# Obtém o produto GPT Premium da configuração
GPT_PRODUCT = get_product('gpt_premium')

# Valor padrão do serviço GPT Premium (obtido do produto ou fallback para 50.0)
GPT_Service_Price = GPT_PRODUCT.price if GPT_PRODUCT else 50.0

# Valores legados para compatibilidade (usar GPT_PRODUCT quando possível)
PAYMENT_AMOUNT = GPT_Service_Price
GPT_LINK = GPT_PRODUCT.link if GPT_PRODUCT else ""

def get_gpt_info_message() -> str:
    """
    Retorna a mensagem informativa sobre o serviço GPT
    """
    return (
        "📢 **Serviço GPT Premium** 📢\n\n"
        "✨ Você sabia que temos um serviço de correção de redação "
        "usando GPT diretamente do site da OpenAI?\n\n"
        "📝 **Como funciona:**\n"
        "• Envie a mensagem /GPT diretamente para o bot ou aqui no grupo\n"
        "• O bot fará uma oferta do serviço de correção de redação\n"
        "• Ao realizar um pagamento único, você terá acesso a um link vitalício para:\n"
        " ✓ correções de redação,\n"
        " ✓ ajuda com exercícios,\n"
        " ✓ cronograma de estudos personalizado,\n"
        "• Conteúdo de estudo personalizado\n\n"
        "🚀 **Tecnologia:** Correção feita pelo GPT-5.2 ou mais recente, "
        "usando a metodologia oficial da matriz de competências do ENEM.\n"
    )

async def get_payment_message(user_id: int = None, pix_data: dict = None, product_id: str = 'gpt_premium') -> str:
    """
    Retorna a mensagem com informações de pagamento
    Gera um código PIX dinâmico via Mercado Pago se não fornecido
    
    Args:
        user_id: ID do usuário
        pix_data: Dados do PIX (opcional)
        product_id: ID do produto (padrão: 'gpt_premium')
    """
    from services.pix_generator import pix_generator
    from services.products_config import get_product
    
    # Obtém informações do produto
    product = get_product(product_id)
    if not product:
        return "❌ Produto não encontrado."
    
    # Gera código PIX via Mercado Pago se não fornecido
    if not pix_data and user_id:
        pix_data = await pix_generator.generate_pix_for_user(user_id, product.price, product_id)
    
    if not pix_data or not pix_data.get('pix_code'):
        return "❌ Erro ao gerar código PIX. Verifique se o Mercado Pago está configurado corretamente."
    
    pix_code = pix_data.get('pix_code')
    payment_id = pix_data.get('payment_id')
    
    message = (
        "💳 **Pagamento**\n\n"
        f"💰 Valor: R$ {product.price:.2f}\n"
        "📱 Forma de pagamento: PIX\n\n"
        "🔑 **Código PIX (Copia e Cola):**\n"
        f"`{pix_code}`\n\n"
    )
    
    # Se tiver QR Code em base64, pode ser enviado como imagem
    if pix_data.get('qr_code_base64'):
        message += "📷 Um QR Code será enviado na próxima mensagem para facilitar o pagamento.\n\n"
    
    message += (
        "📋 **Instruções:**\n"
        f"1. Copie o código PIX acima ou escaneie o QR Code\n"
        "2. Abra seu app de pagamento (banco, carteira digital, etc.)\n"
        f"3. Confirme o pagamento de R$ {product.price:.2f}\n"
        "4. O sistema verificará automaticamente via Mercado Pago\n"
    )

    if product_id == 'bot_access':
        message += "5. Você receberá confirmação assim que o pagamento for aprovado\n\n"
    else:
        message += "5. Você receberá o link vitalício do GPT assim que o pagamento for confirmado\n\n"

    message += (
        "⏰ **Verificação:** O pagamento será verificado automaticamente. "
        "Você será avisado assim que for confirmado."
    )
    
    return message

def get_gpt_access_message(product_id: str = 'gpt_premium') -> str:
    """
    Retorna a mensagem com o link de acesso ao GPT
    
    Args:
        product_id: ID do produto (padrão: 'gpt_premium')
    """
    from services.products_config import get_product
    
    product = get_product(product_id)
    if not product or not product.link:
        return "❌ Produto ou link não encontrado."
    
    return (
        "🎉 **Pagamento Confirmado!** 🎉\n\n"
        f"✅ Seu acesso ao {product.name} foi liberado!\n\n"
        "🔗 **Link Vitalício:**\n"
        f"{product.link}\n\n"
        "📝 **O que você pode fazer:**\n"
        "• Correções de redação ilimitadas\n"
        "• Ajuda com exercícios\n"
        "• Cronograma de estudos personalizado\n"
        "• Conteúdo de estudo personalizado\n\n"
        "💡 Salve este link! Ele é vitalício e você pode usar quantas vezes quiser."
    )

