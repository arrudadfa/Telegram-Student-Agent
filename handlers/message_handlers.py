import asyncio
from aiogram import types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import (
    router, logger, TRIGGER_KEYWORDS, SEARCH_KEYWORDS, ALLOWED_GROUP_IDS, 
    ADMIN_IDS, bot, openai_client, CRONOGRAMA_SYSTEM_PROMPT
)
from services.redacao_service import RedacaoService
from services.cronograma_service import CronogramaService
from services.daily_limit_service import daily_limit_service
from services.payment_service import payment_service
from services.gpt_service import (
    get_gpt_info_message, 
    get_payment_message, 
    get_gpt_access_message
)
from history import chat_history

# Dicionário para rastrear usuários que estão no fluxo de correção de redação
usuarios_aguardando_redacao = {}

# Dicionário para rastrear usuários que estão no fluxo de criação de cronograma
usuarios_aguardando_cronograma = {}

# Cria o menu de botões
def criar_menu_botoes() -> ReplyKeyboardMarkup:
    """Cria o menu de botões com os comandos principais"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✍️ Corrigir Redação"),
                KeyboardButton(text="🔍 Buscar Arquivos")
            ],
            [
                KeyboardButton(text="📅 Criar Cronograma")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

@router.message()
async def handle_message(message: types.Message):
    try:
        if not message.text:
            return
        
        # Verifica se é um grupo permitido (se for mensagem de grupo)
        if message.chat.type in ['group', 'supergroup']:
            if message.chat.id not in ALLOWED_GROUP_IDS:
                logger.debug(f"Mensagem de grupo não permitido ignorada: {message.chat.id}")
                return
        
        # Adiciona mensagem ao histórico
        try:
            chat_history.add_message(message.from_user.id, message.text)
        except Exception as e:
            logger.warning(f"Erro ao adicionar mensagem ao histórico: {e}")
        
        texto = message.text.lower()
        user_id = message.from_user.id
        logger.info(f"Mensagem recebida de {user_id} ({message.chat.type}): {texto[:50]}")

        # PRIORIDADE 1: Verifica se o usuário está aguardando resposta para cronograma
        if user_id in usuarios_aguardando_cronograma:
            await handle_cronograma_response(message)
            return
        
        # PRIORIDADE 2: Verifica se o usuário está aguardando envio de redação
        if user_id in usuarios_aguardando_redacao:
            # Verifica se o usuário ainda pode fazer correção hoje
            if not daily_limit_service.can_make_correction(user_id):
                await message.reply(
                    "❌ Você já utilizou sua correção gratuita de hoje!\n\n"
                    "⏰ O limite é de 1 correção por dia por usuário.\n"
                    "🤖 Você pode comprar o GPT que corrige suas redações, te ajuda com exercícios e monta um cronograma de estudos personalizado.\n"
                    " Basta digitar /GPT para obter mais informações."
                )
                # Remove o usuário do fluxo
                del usuarios_aguardando_redacao[user_id]
                return
            
            # Processa a correção da redação
            notas, feedback = await RedacaoService.corrigir_redacao(message.text)
            if feedback:
                await message.reply(feedback)
                # Registra a correção no contador diário
                daily_limit_service.register_correction(user_id)
            # Remove o usuário do fluxo após processar
            del usuarios_aguardando_redacao[user_id]
            return

        # PRIORIDADE 3: Verifica comandos específicos ANTES de processar palavras-chave
        if texto.startswith('/start') or texto == '/start':
            await handle_start_command(message)
            return
        
        if texto.startswith('/gpt') or texto == '/gpt':
            await handle_gpt_command(message)
            return
        
        if texto.startswith('/redação') or texto == '/redação' or texto == '/redacao' or texto.lower() == '✍️ corrigir redação':
            await handle_redacao_command(message)
            return
        
        if texto.startswith('/arquivo') or texto == '/arquivo' or texto.lower() == '🔍 buscar arquivos':
            await handle_arquivo_command(message)
            return
        
        if texto.startswith('/cronograma') or texto.lower() == '📅 criar cronograma':
            await handle_cronograma_command(message)
            return
        
        # Comando administrativo para confirmar pagamento
        if texto.startswith('/confirmar_pagamento') and user_id in ADMIN_IDS:
            await handle_confirm_payment_command(message)
            return

        # PRIORIDADE 4: Verifica se a mensagem contém palavras-chave de trigger
        trigger_encontrado = [keyword for keyword in TRIGGER_KEYWORDS if keyword in texto]
        contem_trigger = len(trigger_encontrado) > 0
        
        # Verifica se o texto contém palavras relacionadas a redação (independente de trigger)
        palavras_redacao = ['redação', 'redacao', 'corrige', 'corrigir', 'corrija', 'correção', 'correcao']
        contem_redacao = any(palavra in texto for palavra in palavras_redacao)
        
        # PRIORIDADE 5: Verifica se contém palavras-chave de busca (após comandos e triggers)
        search_keyword_encontrado = [keyword for keyword in SEARCH_KEYWORDS if keyword.lower() in texto.lower()]
        contem_search_keyword = len(search_keyword_encontrado) > 0
        
        logger.info(f"DEBUG - Texto: '{texto[:100]}' | Trigger: {contem_trigger} ({trigger_encontrado}) | Redação: {contem_redacao} | Busca: {contem_search_keyword} ({search_keyword_encontrado})")
        
        # Se contém palavra-chave de busca, realiza busca no CSV
        if contem_search_keyword:
            from services.file_search_service import file_search_service
            
            try:
                # Busca por todas as palavras-chave encontradas
                resultados = file_search_service.search_files_multiple_terms(search_keyword_encontrado, limit=4)
                
                if resultados:
                    mensagem_busca = "🔍 Aqui está uma sugestão para o que você está buscando:\n\n"
                    
                    for arquivo in resultados:
                        file_name = arquivo.get('file_name', 'Arquivo sem nome')
                        link = arquivo.get('link_completo', '')
                        
                        # Escapa caracteres especiais do HTML
                        file_name_escaped = file_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        
                        if link:
                            # Usa HTML para criar link clicável
                            mensagem_busca += f"📄 <b>{file_name_escaped}</b>\n"
                            mensagem_busca += f"🔗 <a href=\"{link}\">{link}</a>\n\n"
                        else:
                            mensagem_busca += f"📄 <b>{file_name_escaped}</b>\n\n"
                    
                    await message.reply(mensagem_busca, parse_mode='HTML')
                    logger.info(f"Resultados de busca enviados para usuário {user_id}: {len(resultados)} arquivo(s) (termos: {search_keyword_encontrado})")
                    return
                else:
                    logger.info(f"Nenhum arquivo encontrado para termos '{search_keyword_encontrado}'")
            except Exception as e:
                logger.error(f"Erro ao buscar arquivos: {e}", exc_info=True)
        
        if contem_trigger or contem_redacao:
            # Se contém palavras de redação, trata como correção de redação
            if contem_redacao:
                # Comportamento para redação: mantém o fluxo atual
                # Verifica se o usuário ainda pode fazer correção hoje
                if not daily_limit_service.can_make_correction(user_id):
                    await message.reply(
                        "❌ Você já utilizou sua correção gratuita de hoje!\n\n"
                        "⏰ O limite é de 1 correção por dia por usuário.\n"
                        "🤖 Você pode comprar o GPT que corrige suas redações, te ajuda com exercícios e monta um cronograma de estudos personalizado.\n"
                        " Basta digitar /GPT para obter mais informações."

                    )
                    return
                
                # Oferece o serviço de correção de redação
                oferta = (
                    "👋 Olá! Posso ajudar você com a correção da sua redação!\n\n"
                    "📝 Envie sua redação aqui e eu vou corrigi-la usando a metodologia "
                    "da matriz de competências do ENEM, fornecendo:\n"
                    "• Nota de 0 a 200 para cada uma das 5 competências\n"
                    "• Feedback detalhado sobre cada competência\n"
                    "• Nota final total\n\n"
                    "🎯 **Limite:** 1 correção gratuita por dia\n\n"
                    "✍️ Por favor, envie sua redação completa agora:"
                )
                await message.reply(oferta)
                # Marca o usuário como aguardando redação
                usuarios_aguardando_redacao[user_id] = True
                logger.info(f"Usuário {user_id} marcado como aguardando redação")
                return
            
            # Comportamento para outras triggers (não relacionadas a redação): usa GPT-4o
            if contem_trigger:
                from services.openai_service import get_openai_response
                
                try:
                    logger.info(f"Processando mensagem com GPT-4o para usuário {user_id}")
                    # Obtém resposta do GPT-4o
                    responses = await get_openai_response(message.text)
                    
                    # Envia resposta(s) - pode ser dividida em múltiplas mensagens se muito longa
                    for response_text in responses:
                        await message.reply(response_text)
                    
                    logger.info(f"Resposta GPT-4o enviada para usuário {user_id}")
                except Exception as e:
                    logger.error(f"Erro ao obter resposta do GPT-4o: {e}", exc_info=True)
                    await message.reply(
                        "❌ Desculpe, ocorreu um erro ao processar sua mensagem. "
                        "Tente novamente em alguns instantes."
                    )
                return
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
        try:
            if message.text:
                await message.reply("❌ Ocorreu um erro ao processar sua mensagem. Tente novamente.")
        except:
            pass

async def handle_start_command(message: types.Message):
    """
    Handler para o comando /start - mostra o menu de botões
    """
    welcome_message = (
        "👋 Olá! Bem-vindo ao Bot de Estudos!\n\n"
        "🤖 Eu posso ajudar você com:\n"
        "• ✍️ Correção de redações (1 por dia gratuitamente)\n"
        "• 🔍 Busca de arquivos e materiais de estudo\n"
        "• 📅 Criação de cronogramas personalizados\n"
        "• 💬 Resolução de exercícios e dúvidas\n\n"
        "📌 Use os botões abaixo ou digite os comandos:\n"
        "/redação - Corrigir redação\n"
        "/arquivo - Buscar arquivos\n"
        "/cronograma - Criar cronograma\n"
        "/GPT - Conhecer serviço premium"
    )
    
    keyboard = criar_menu_botoes()
    await message.reply(welcome_message, reply_markup=keyboard)
    logger.info(f"Menu de botões enviado para usuário {message.from_user.id}")

async def handle_redacao_command(message: types.Message):
    """
    Handler para o comando /redação - inicia fluxo de correção
    """
    user_id = message.from_user.id
    
    # Verifica se o usuário ainda pode fazer correção hoje
    if not daily_limit_service.can_make_correction(user_id):
        await message.reply(
            "❌ Você já utilizou sua correção gratuita de hoje!\n\n"
            "⏰ O limite é de 1 correção por dia por usuário.\n"
            "🤖 Você pode comprar o GPT que corrige suas redações, te ajuda com exercícios e monta um cronograma de estudos personalizado.\n"
            " Basta digitar /GPT para obter mais informações."
        )
        return
    
    # Oferece o serviço de correção de redação
    oferta = (
        "👋 Olá! Posso ajudar você com a correção da sua redação!\n\n"
        "📝 Envie sua redação aqui e eu vou corrigi-la usando a metodologia "
        "da matriz de competências do ENEM, fornecendo:\n"
        "• Nota de 0 a 200 para cada uma das 5 competências\n"
        "• Feedback detalhado sobre cada competência\n"
        "• Nota final total\n\n"
        "🎯 **Limite:** 1 correção gratuita por dia\n\n"
        "✍️ Por favor, envie sua redação completa agora:"
    )
    await message.reply(oferta, reply_markup=ReplyKeyboardRemove())
    # Marca o usuário como aguardando redação
    usuarios_aguardando_redacao[user_id] = True
    logger.info(f"Usuário {user_id} marcado como aguardando redação")

async def handle_arquivo_command(message: types.Message):
    """
    Handler para o comando /arquivo - permite buscar arquivos
    """
    mensagem = (
        "🔍 **Busca de Arquivos**\n\n"
        "Para buscar arquivos, basta digitar palavras-chave relacionadas ao que você procura.\n\n"
        "📚 **Exemplos de buscas:**\n"
        "• Digite 'FUVEST' para encontrar materiais da FUVEST\n"
        "• Digite 'ENEM' para encontrar materiais do ENEM\n"
        "• Digite 'cronograma' para encontrar cronogramas\n"
        "• Digite 'alguém tem' seguido do material desejado\n\n"
        "💡 **Dica:** Quanto mais específica sua busca, melhores serão os resultados!\n\n"
        "Digite agora o que você está procurando:"
    )
    await message.reply(mensagem, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())

async def handle_cronograma_command(message: types.Message):
    """
    Handler para o comando /cronograma - inicia fluxo de criação de cronograma
    """
    user_id = message.from_user.id
    
    pergunta = (
        "📅 **Criação de Cronograma Personalizado**\n\n"
        "Para criar um cronograma de estudos ideal para você, preciso de algumas informações:\n\n"
        "❓ **Por favor, responda com as seguintes informações:**\n"
        "1️⃣ Quanto tempo diário você tem disponível para estudar?\n"
        "2️⃣ Qual matéria você tem mais dificuldade?\n"
        "3️⃣ Qual é a data estimada da prova?\n\n"
        "💡 **Exemplo de resposta:**\n"
        "\"Tenho 4 horas por dia, tenho dificuldade em Matemática, e a prova é em 15 de novembro de 2024\"\n\n"
        "📝 Envie sua resposta agora:"
    )
    
    await message.reply(pergunta, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    # Marca o usuário como aguardando resposta para cronograma
    usuarios_aguardando_cronograma[user_id] = True
    logger.info(f"Usuário {user_id} marcado como aguardando resposta para cronograma")

async def handle_cronograma_response(message: types.Message):
    """
    Handler para processar a resposta do usuário sobre cronograma
    """
    user_id = message.from_user.id
    resposta_usuario = message.text
    
    try:
        logger.info(f"Processando resposta de cronograma do usuário {user_id}: {resposta_usuario[:100]}")
        
        # Remove o usuário do fluxo antes de processar
        del usuarios_aguardando_cronograma[user_id]
        
        # Envia mensagem de processamento
        await message.reply("⏳ Gerando seu cronograma personalizado... Aguarde um momento!")
        
        # Chama o GPT com o CRONOGRAMA_SYSTEM_PROMPT
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": CRONOGRAMA_SYSTEM_PROMPT},
                    {"role": "user", "content": resposta_usuario}
                ],
                max_tokens=2000,
                temperature=0.7,
                presence_penalty=0.6,
                frequency_penalty=0.2
            )
            
            if response and response.choices:
                cronograma = response.choices[0].message.content.strip()
                
                # Divide a resposta se for muito longa
                if len(cronograma) > 4000:
                    partes = [cronograma[i:i+4000] for i in range(0, len(cronograma), 4000)]
                    for parte in partes:
                        await message.reply(parte)
                else:
                    await message.reply(cronograma)
                
                logger.info(f"Cronograma gerado e enviado para usuário {user_id}")
            else:
                await message.reply(
                    "❌ Desculpe, não consegui gerar o cronograma. "
                    "Tente novamente com informações mais detalhadas."
                )
        except Exception as e:
            logger.error(f"Erro ao gerar cronograma com GPT: {e}", exc_info=True)
            await message.reply(
                "❌ Ocorreu um erro ao gerar o cronograma. "
                "Tente novamente em alguns instantes."
            )
    except Exception as e:
        logger.error(f"Erro ao processar resposta de cronograma: {e}", exc_info=True)
        await message.reply("❌ Ocorreu um erro ao processar sua resposta. Tente novamente.")

async def handle_gpt_command(message: types.Message):
    """
    Handler para o comando /GPT
    """
    user_id = message.from_user.id
    
    # Verifica se o usuário já tem acesso pago
    if payment_service.is_paid_user(user_id):
        # Verifica se é uma conversa privada (não grupo)
        if message.chat.type in ['group', 'supergroup']:
            # Em grupos, apenas informa que tem acesso, sem enviar o link
            await message.reply(
                "✅ Você já tem acesso ao GPT Premium!\n\n"
                "💬 Por favor, me envie uma mensagem privada para receber seu link vitalício."
            )
            return
        
        # Em conversas privadas, envia o link
        from services.products_config import get_product
        product = get_product('gpt_premium')
        link = product.link if product else "Link não disponível"
        await message.reply(
            "✅ Você já tem acesso ao GPT Premium!\n\n"
            f"🔗 Seu link vitalício:\n{link}\n\n"
            "💡 Salve este link! Ele é vitalício e você pode usar quantas vezes quiser."
        )
        return
    
    # Verifica se é uma conversa privada (não grupo)
    if message.chat.type in ['group', 'supergroup']:
        # Em grupos, apenas informa sobre o serviço e pede mensagem privada
        info_message = get_gpt_info_message()
        await message.reply(info_message, parse_mode='Markdown')
        await message.reply(
            "🔒 **Para sua segurança, o código PIX só pode ser enviado em conversas privadas.**\n\n"
            "💬 Por favor, me envie uma mensagem privada para receber o código PIX e realizar o pagamento."
        )
        return
    
    # Em conversas privadas, continua com o fluxo de pagamento
    # Envia informações sobre o serviço
    info_message = get_gpt_info_message()
    await message.reply(info_message, parse_mode='Markdown')
    
    # Aguarda um pouco antes de enviar a mensagem de pagamento
    await asyncio.sleep(1)
    
    # Gera código PIX dinâmico via Mercado Pago para o usuário
    from services.pix_generator import pix_generator
    product_id = 'gpt_premium'  # Produto padrão
    pix_data = await pix_generator.generate_pix_for_user(user_id, product_id=product_id)
    
    if not pix_data:
        await message.reply(
            "❌ Erro ao gerar código PIX. "
            "O serviço de pagamento pode estar temporariamente indisponível. "
            "Tente novamente em alguns instantes."
        )
        return
    
    # Envia informações de pagamento com código PIX gerado
    payment_msg = await get_payment_message(user_id, pix_data, product_id=product_id)
    await message.reply(payment_msg, parse_mode='Markdown')
    
    # Se tiver QR Code, envia como imagem
    if pix_data.get('qr_code_base64'):
        try:
            import base64
            from io import BytesIO  # pyright: ignore[reportUnusedImport]
            from aiogram.types import BufferedInputFile
            
            qr_image_data = base64.b64decode(pix_data['qr_code_base64'])
            qr_file = BufferedInputFile(qr_image_data, filename="qrcode.png")
            await message.answer_photo(qr_file, caption="📷 QR Code para pagamento PIX")
        except Exception as e:
            logger.error(f"Erro ao enviar QR Code: {e}")
    
    # Registra pagamento pendente com payment_id do Mercado Pago
    payment_id = pix_data.get('payment_id')
    payment_service.register_pending_payment(user_id, payment_reference=payment_id, pix_code=pix_data.get('pix_code'), product_id=product_id)
    
    # Inicia verificação de pagamento em background
    asyncio.create_task(check_payment_periodically(user_id, message))

async def check_payment_periodically(user_id: int, message: types.Message, max_checks: int = 60, interval: int = 30):
    """
    Verifica periodicamente se o pagamento foi realizado
    Verifica a cada 30 segundos por até 30 minutos (60 verificações)
    """
    from services.payment_service import payment_service
    from config import bot
    
    for check in range(max_checks):
        await asyncio.sleep(interval)
        
        # Verifica se o pagamento foi confirmado
        if payment_service.is_paid_user(user_id):
            # Envia mensagem de acesso SEMPRE via mensagem privada (nunca em grupos)
            access_message = get_gpt_access_message('gpt_premium')
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=access_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Link do GPT enviado via mensagem privada para usuário {user_id}")
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem de acesso para {user_id}: {e}")
            break
        
        # Tenta verificar pagamento consultando o Mercado Pago
        if await payment_service.verify_payment_for_user(user_id):
            # Pagamento confirmado automaticamente - SEMPRE via mensagem privada
            access_message = get_gpt_access_message('gpt_premium')
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=access_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Link do GPT enviado via mensagem privada para usuário {user_id}")
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem de acesso para {user_id}: {e}")
            break
        
        # Verifica se há pagamento pendente
        pending = payment_service.get_pending_payment(user_id)
        if pending:
            logger.info(f"Aguardando confirmação de pagamento para usuário {user_id} (verificação {check + 1}/{max_checks})")
    
    logger.info(f"Verificação de pagamento finalizada para usuário {user_id}")

async def handle_confirm_payment_command(message: types.Message):
    """
    Handler administrativo para confirmar pagamento manualmente
    Uso: /confirmar_pagamento <user_id>
    """
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply(
                "❌ Uso incorreto!\n\n"
                "📝 Formato: /confirmar_pagamento <user_id>\n"
                "Exemplo: /confirmar_pagamento 123456789"
            )
            return
        
        user_id_to_confirm = int(parts[1])
        
        # Confirma o pagamento
        if payment_service.confirm_payment(user_id_to_confirm):
            # Envia mensagem de acesso ao usuário
            try:
                access_message = get_gpt_access_message('gpt_premium')
                await bot.send_message(
                    chat_id=user_id_to_confirm,
                    text=access_message,
                    parse_mode='Markdown'
                )
                await message.reply(
                    f"✅ Pagamento confirmado para usuário {user_id_to_confirm}!\n"
                    "📨 Link do GPT enviado ao usuário."
                )
            except Exception as e:
                from services.products_config import get_product
                product = get_product('gpt_premium')
                link = product.link if product else "Link não disponível"
                await message.reply(
                    f"✅ Pagamento confirmado para usuário {user_id_to_confirm}!\n"
                    f"⚠️ Erro ao enviar mensagem ao usuário: {e}\n"
                    f"🔗 Link do GPT: {link}"
                )
        else:
            await message.reply(
                f"ℹ️ Usuário {user_id_to_confirm} já tinha acesso confirmado."
            )
    except ValueError:
        await message.reply("❌ ID de usuário inválido!")
    except Exception as e:
        logger.error(f"Erro ao confirmar pagamento: {e}")
        await message.reply(f"❌ Erro ao confirmar pagamento: {e}")

# Manipulador para mensagens de boas-vindas a novos membros
@router.chat_member()
async def welcome_new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        new_member_name = event.new_chat_member.user.full_name
        welcome_message = f"Bem-vindo ao grupo, {new_member_name}!"
        await bot.send_message(event.chat.id, welcome_message)