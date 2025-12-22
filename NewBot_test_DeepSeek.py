import os
from python_telegram_bot import TelegramBot

def main():
    # Configurar o bot Telegram com as credenciais
    token = os.getenv('TELEGRAM_TOKEN')
    bot = TelegramBot(token, use_web_hook=True)

    # Configurar o caminho para armazenar as listagens
    listings_path = 'listings'

    # Configurar os caminhos para armazenar as imagens das listagens
    images_path = 'images'

    # Configurar a largura da imagem
    image_width = 500

    # Configurar a taxa de juros do cartão de crédito
    card_payment_rate = 0.0275

    # Configurar os limites de idade para a idade de compra
    min_age = 18
    max_age = 999999

    # Configurar o caminho para armazenar as informações dos chatos
    chats_path = 'chats'

    # Inicializar os dicionários para armazenar as listagens e os chatos
    listings = {}
    chats = {}

    def get_listings():
        """Obter informações de listagens do Telegram."""
        try:
            updates = bot.get_updates()
            if updates.last_update_id  > 0:
                for u in updates.Units:
                    if isinstance(u, int):
                        continue
                    chat_id, message_date, message_id = u
                    if not message_id.startswith('photo'):
                        continue

                    name = os.path.basename(message_id)
                    image_url = f'https://t.me/{chat_id}/message{message_id}'

                    # Obter as informações do chat
                    chat_info = get_chat_info(chat_id)

                    # Verificar se已经有 lista para essa imagem
                    if chat_info in listings:
                        if any(imagem['id'] == name for imagem in listings[chat_info]):
                            continue

                    # Cadastrar a nova lista
                    new_listing = {
                        'id': len(listings) + 1,
                        'chat_id': chat_id,
                        'message_date': message_date,
                        'name': name,
                        'description': get_description(name),
                        'price': card_payment_rate * int(name.replace(' ', '').replace('.','').replace('-','')) if
'.' in name else int(name.replace(' ', '').replace('.','-')),
                        'images': [image_url],
                    }

                    listings[chat_info] = new_listing

                    # Salvar a lista no arquivo
                    with open(f'{listings_path}/{new_listing['id']}.json', 'w') as f:
                        f.write(str(new_listing))

        except Exception as e:
            print(f'Erro na obtenção de listagens: {e}')

    def get_chat_info(chat_id):
        """Obter informações do chat do Telegram."""
        try:
            chat = bot.get_chat(chat_id)
            if not chat:
                return None

            name = chat['title']
            last_name = chat.get('last_name')

            birth_date = chat.get('user', {}).get('bdate')

            return {'name': name, 'last_name': last_name, 'birth_date': birth_date}
        except Exception as e:
            print(f'Erro na obtenção de informações do chat {chat_id}: {e}')
            return None

    def get_description(name):
        """Obter uma breve descrição da imagem."""
        try:
            # Aqui você pode implementar lógica para analisar a imagem
            # por exemplo, using OpenCV para extrair características
            # e geração de texto alternativo
            # Aqui estamos apenas retornando um exemplo básico
            return f'Imagem_{name}_desc'
        except Exception as e:
            print(f'Erro na geração de descrição: {e}')
            return None

    def create_listing(name, description, price):
        """Cadastrar uma nova lista na base de dados."""
        try:
            new_listing = {
                'id': len(listings) + 1,
                'chat_id': None,
                'message_date': None,
                'name': name,
                'description': description or '',
                'price': price,
                'images': []
            }

            listings[len(listings)+1] = new_listing

            with open(f'{listings_path}/{new_listing["id"]}.json', 'w') as f:
                f.write(str(new_listing))
        except Exception as e:
            print(f'Erro na criação da lista: {e}')

    def handle_payment(chat_id, image_url):
        """Tratamento do pagamento de uma lista."""
        try:
            # Aqui você pode implementar a lógica para processesar o pagamento
            # por exemplo, usando um serviço de cartão de crédito
            payment = {
                'status': 'pending',
                'description': f'Payment for Imagem_{image_url.split("/")[-1]}_id{chat_id}',
                'timestamp': os.getenv('CURRENT_TIMESTAMP'),
                'payment_method': 'credit_card',
                'amount': int(image_url.split('/')[-1]),
                'tx reference': chat_id
            }

            with open(f'{listings_path}/payments/{chat_id}.json', 'w') as f:
                f.write(str(payment))
        except Exception as e:
            print(f'Erro no pagamento: {e}')

    def send_confirmation(chat_id, payment Reference):
        """Enviar confirmação de compra via bot."""
        try:
            message = f'Confirmação de compra:\nId da imagem: {image_url}\nPreço: R$ {price}\nData:{message_date}\nNome do usuário: {last_name}'
            bot.send_message(chat_id, message)

            #Envia o link para visualização
            bot.send_message(chat_id, image_url)
        except Exception as e:
            print(f'Erro na confirmação: {e}')

    def extract_info_from_chat(chat_id):
        """Extrair informações do chat."""
        try:
            chat = get_chat_info(chat_id)

            if not chat:
                return None

            return {
                'chat_id': chat_id,
                'name': chat['name'],
                'last_name': chat.get('last_name'),
                'birth_date': chat.get('user', {}).get('bdate')
            }
        except Exception as e:
            print(f'Erro na extração de informações do chat {chat_id}: {e}')
            return None

    def send_message(chat_id, text):
        """Enviar mensagem via bot."""
        try:
            bot.send_message(chat_id, text)
        except Exception as e:
            print(f'Erro na enviação da mensagem para o chat {chat_id}: {e}')

    if __name__ == '__main__':
        # Iniciar o bot
        bot.start_polling()

        while True:
            # Processar upload de imagens
            get_listings()

            # Processar listagens
            for chat_info in listings:
                chat_id = chat_info['chat_id']

                if not chat_id or chat_id == '':
                    continue

                listings[chat_info] = create_listing(
                    name=next_name,
                    description=get_description(name),
                    price=int(name.replace(' ', '').replace('.','').replace('-',''))
                )

                # Processar pagamento
                handle_payment(chat_id, image_url)

                # Enviar confirmação de compra
                send_confirmation(chat_id, payment_reference)

            main()

if __name__ == '__main__':
    main()