# 🔐 Configuração de Segurança - Credenciais

## ⚠️ IMPORTANTE

Todos os tokens, senhas e chaves de API foram movidos para variáveis de ambiente para maior segurança.

## 📋 Como Configurar

### 1. Criar arquivo `.env`

Copie o arquivo `.env.example` para `.env`:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2. Preencher o arquivo `.env`

Abra o arquivo `.env` e preencha com suas credenciais reais:

```env
# Token do Bot do Telegram
# Obtenha em: https://t.me/BotFather
TELEGRAM_BOT_TOKEN=seu_token_aqui

# Chave da API OpenAI
# Obtenha em: https://platform.openai.com/api-keys
OPENAI_API_KEY=sua_chave_aqui

# URL do Ngrok para webhook
NGROK_URL=https://seu-ngrok-url.ngrok-free.app

# Porta local para o webhook
WEBHOOK_PORT=8080

# Credenciais do Mercado Pago
# Obtenha em: https://www.mercadopago.com.br/developers/panel/credentials
MERCADOPAGO_ACCESS_TOKEN=seu_token_aqui
MERCADOPAGO_PUBLIC_KEY=sua_chave_aqui
```

### 3. Verificar se está funcionando

Execute o bot e verifique os logs. Você deve ver:

```
Token do Telegram carregado: 5942471133...
Token da OpenAI carregado: sk-yISLcQPi...
Ngrok URL configurado: https://...
```

Se aparecer erro, verifique se o arquivo `.env` está na raiz do projeto.

## 🔒 Segurança

- ✅ O arquivo `.env` está no `.gitignore` e **NUNCA** será commitado
- ✅ O arquivo `.env.example` serve como template (sem credenciais reais)
- ✅ Todos os tokens são carregados de variáveis de ambiente
- ✅ Nenhuma credencial está hardcoded no código

## 📝 Variáveis de Ambiente Obrigatórias

- `TELEGRAM_BOT_TOKEN` - **Obrigatório**
- `OPENAI_API_KEY` - **Obrigatório**

## 📝 Variáveis de Ambiente Opcionais

- `NGROK_URL` - Necessário apenas se usar webhook
- `WEBHOOK_PORT` - Padrão: 8080
- `MERCADOPAGO_ACCESS_TOKEN` - Necessário apenas para pagamentos
- `MERCADOPAGO_PUBLIC_KEY` - Necessário apenas para pagamentos

## 🚨 Se o bot não iniciar

Se você receber erros como:
```
ValueError: TELEGRAM_BOT_TOKEN não encontrado! Configure no arquivo .env
```

1. Verifique se o arquivo `.env` existe na raiz do projeto
2. Verifique se as variáveis estão escritas corretamente (sem espaços, sem aspas)
3. Verifique se não há erros de digitação nos nomes das variáveis

## 📚 Onde Obter as Credenciais

- **Telegram Bot Token**: https://t.me/BotFather
- **OpenAI API Key**: https://platform.openai.com/api-keys
- **Mercado Pago**: https://www.mercadopago.com.br/developers/panel/credentials
- **Ngrok**: https://ngrok.com/

