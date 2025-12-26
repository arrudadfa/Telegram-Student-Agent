# Configuração do Mercado Pago

Este bot usa a API do Mercado Pago para gerar códigos PIX dinamicamente e verificar pagamentos automaticamente.

## Passo 1: Criar Conta no Mercado Pago

1. Acesse https://www.mercadopago.com.br/
2. Crie uma conta (pode ser pessoa física ou jurídica)
3. Complete a verificação da conta

## Passo 2: Obter Credenciais de Acesso

1. Acesse o painel de desenvolvedores: https://www.mercadopago.com.br/developers/panel
2. Crie uma nova aplicação
3. Copie as credenciais:
   - **Access Token** (Token de Acesso)
   - **Public Key** (Chave Pública - opcional)

## Passo 3: Configurar no Bot

### Opção 1: Variáveis de Ambiente (Recomendado)

Crie ou edite o arquivo `.env` na raiz do projeto:

```env
MERCADOPAGO_ACCESS_TOKEN=seu_access_token_aqui
MERCADOPAGO_PUBLIC_KEY=sua_public_key_aqui
```

### Opção 2: Configuração Direta

Edite o arquivo `config.py`:

```python
MERCADOPAGO_ACCESS_TOKEN = 'APP_USR-5199900670997861-011920-7ec613e6e5f0f5405f5a5795c51a8078-135152840'
MERCADOPAGO_PUBLIC_KEY = 'APP_USR-c9800f79-6a4b-418e-8e70-7c3408c89853'
```

## Passo 4: Configurar Webhook no Mercado Pago

1. No painel do Mercado Pago, vá em **Webhooks**
2. Configure a URL do webhook:
   ```
   https://b597ffb1a237.ngrok-free.app/webhook/payment
   ```
3. Selecione os eventos:
   - `payment`
   - `payment.updated`

## Passo 5: Testar

1. Inicie o bot: `python main.py`
2. Digite `/GPT` no Telegram
3. O bot deve gerar um código PIX via Mercado Pago
4. Faça um pagamento de teste
5. O webhook deve confirmar automaticamente

## Modo Sandbox (Testes)

Para testar sem usar dinheiro real:

1. Use as credenciais do **Sandbox** (ambiente de testes)
2. Crie usuários de teste no painel do Mercado Pago
3. Use cartões de teste para simular pagamentos

## Documentação da API

- API de Pagamentos: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/landing
- Webhooks: https://www.mercadopago.com.br/developers/pt/docs/your-integrations/notifications/webhooks

## Troubleshooting

### Erro: "Mercado Pago não está configurado"
- Verifique se o `MERCADOPAGO_ACCESS_TOKEN` está configurado
- Verifique se o token está correto e válido

### Erro: "Erro ao criar pagamento PIX"
- Verifique se a conta do Mercado Pago está verificada
- Verifique se o Access Token tem permissões para criar pagamentos
- Verifique os logs para mais detalhes

### Webhook não está recebendo notificações
- Verifique se o ngrok está rodando
- Verifique se a URL do webhook está correta no painel do Mercado Pago
- Teste o endpoint manualmente: `curl https://b597ffb1a237.ngrok-free.app/health`

