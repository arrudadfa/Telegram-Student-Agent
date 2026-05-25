# 📚 Estrutura e Fluxo do Código - Telegram Student Agent Bot

## 📁 Estrutura de Diretórios

```
Telegram Student Agent/
│
├── main.py                          # Ponto de entrada da aplicação
├── config.py                        # Configurações globais (tokens, IDs, constantes)
├── history.py                       # Gerenciamento de histórico de conversas
│
├── handlers/                        # Handlers de mensagens do bot
│   └── message_handlers.py         # Processamento de todas as mensagens
│
├── services/                        # Serviços de negócio
│   ├── products_config.py          # Configuração centralizada de produtos
│   ├── gpt_service.py              # Serviços relacionados ao GPT Premium
│   ├── payment_service.py          # Gerenciamento de pagamentos
│   ├── pix_generator.py            # Geração de códigos PIX via Mercado Pago
│   ├── mercadopago_service.py      # Integração com API do Mercado Pago
│   ├── redacao_service.py          # Correção de redações usando OpenAI
│   ├── daily_limit_service.py      # Controle de limites diários
│   ├── propaganda_service.py       # Propagandas diárias automáticas
│   ├── file_search_service.py      # Busca de arquivos por palavras-chave
│   └── openai_service.py           # Respostas GPT para triggers gerais
│
├── webhook/                         # Webhooks para pagamentos
│   ├── payment_webhook.py          # Handler de webhooks do Mercado Pago
│   └── README.md                    # Documentação do webhook
│
└── data/                            # Dados persistentes
    ├── paid_users.json             # Usuários que pagaram
    └── pix_mappings.json           # Mapeamento payment_id -> user_id
```

---

## 🚀 Fluxo de Inicialização

### 1. **main.py** - Ponto de Entrada

```python
main()
├── Registra handlers (message_handlers.router)
├── Inicia servidor webhook em background (porta 8080)
├── Inicia scheduler de propagandas diárias
├── Verifica conexão do bot (bot.get_me())
└── Inicia polling do Telegram (dp.start_polling)
```

**Sequência de inicialização:**
1. Carrega configurações do `config.py`
2. Inicializa bot, dispatcher e router
3. Configura Mercado Pago (se token disponível)
4. Registra handlers de mensagens
5. Inicia servidor webhook em background
6. Inicia scheduler de propagandas
7. Inicia polling para receber mensagens

---

## 📨 Fluxo de Processamento de Mensagens

### **handlers/message_handlers.py**

```
Mensagem recebida
    │
    ├─→ Verifica se tem texto
    │   └─→ Se não: retorna
    │
    ├─→ Verifica se é grupo permitido
    │   └─→ Se não: retorna (ignora)
    │
    ├─→ Adiciona ao histórico (history.py)
    │
    └─→ Processa mensagem:
        │
        ├─→ Usuário aguardando redação?
        │   └─→ RedacaoService.corrigir_redacao()
        │       └─→ Verifica limite diário
        │       └─→ Chama OpenAI API
        │       └─→ Retorna feedback
        │
        ├─→ Contém palavras-chave de trigger?
        │   └─→ Oferece correção de redação
        │       └─→ Marca usuário como aguardando redação
        │
        ├─→ Comando /gpt?
        │   └─→ handle_gpt_command()
        │
        ├─→ Comando /cronograma?
        │   └─→ (em desenvolvimento)
        │
        └─→ Comando /confirmar_pagamento (admin)?
            └─→ handle_confirm_payment_command()
```

---

## 💳 Fluxo de Pagamento - GPT Premium

### **Cenário 1: Usuário solicita acesso via `/gpt`**

```
Usuário envia /gpt
    │
    ├─→ Verifica se já tem acesso pago
    │   ├─→ Se SIM (em grupo):
    │   │   └─→ "Você já tem acesso! Envie mensagem privada."
    │   │
    │   └─→ Se SIM (privado):
    │       └─→ Envia link vitalício
    │
    └─→ Se NÃO tem acesso:
        │
        ├─→ Verifica tipo de chat
        │   ├─→ Se GRUPO:
        │   │   └─→ Informa serviço + pede mensagem privada
        │   │
        │   └─→ Se PRIVADO:
        │       │
        │       ├─→ Envia informações do serviço
        │       │
        │       ├─→ Gera código PIX (pix_generator.py)
        │       │   └─→ Consulta Mercado Pago API
        │       │   └─→ Cria pagamento PIX
        │       │   └─→ Retorna: payment_id, pix_code, qr_code_base64
        │       │
        │       ├─→ Envia mensagem de pagamento
        │       │   └─→ Código PIX (copia e cola)
        │       │   └─→ QR Code (imagem)
        │       │
        │       ├─→ Registra pagamento pendente
        │       │   └─→ payment_service.register_pending_payment()
        │       │   └─→ Salva em data/paid_users.json
        │       │
        │       └─→ Inicia verificação periódica (background)
        │           └─→ check_payment_periodically()
        │               └─→ Verifica a cada 30s por 30min
        │               └─→ Consulta Mercado Pago API
        │               └─→ Se aprovado: envia link (via privado)
```

### **Cenário 2: Webhook do Mercado Pago (pagamento confirmado)**

```
Mercado Pago envia webhook
    │
    ├─→ payment_webhook.py recebe requisição
    │   └─→ /webhook/payment
    │
    ├─→ Extrai payment_id do webhook
    │
    ├─→ Consulta Mercado Pago API
    │   └─→ Obtém status completo do pagamento
    │
    ├─→ Identifica user_id
    │   └─→ Via pix_generator.get_user_by_payment_id()
    │   └─→ Ou via metadata do pagamento
    │
    ├─→ Verifica status = 'approved'
    │
    ├─→ Confirma pagamento
    │   └─→ payment_service.confirm_payment()
    │       ├─→ Adiciona user_id a paid_users
    │       ├─→ Remove de pending_payments
    │       └─→ Limpa mapeamento PIX
    │
    └─→ Envia link vitalício (via mensagem privada)
        └─→ bot.send_message(chat_id=user_id)
```

### **Cenário 3: Verificação periódica (fallback)**

```
check_payment_periodically() (executando em background)
    │
    ├─→ A cada 30 segundos:
    │   │
    │   ├─→ Verifica se já está pago
    │   │   └─→ Se SIM: envia link e para
    │   │
    │   ├─→ Consulta Mercado Pago API
    │   │   └─→ payment_service.verify_payment_for_user()
    │   │       └─→ Obtém payment_id do usuário
    │   │       └─→ Consulta status na API
    │   │       └─→ Se 'approved': confirma pagamento
    │   │
    │   └─→ Se ainda pendente: continua verificando
    │
    └─→ Após 60 verificações (30min): para
```

---

## 📝 Fluxo de Correção de Redação

```
Mensagem contém palavra-chave de trigger
    │
    ├─→ Verifica limite diário
    │   └─→ daily_limit_service.can_make_correction()
    │       └─→ Verifica se já fez correção hoje
    │
    ├─→ Se pode fazer correção:
    │   │
    │   ├─→ Oferece serviço de correção
    │   │
    │   └─→ Marca usuário como aguardando redação
    │       └─→ usuarios_aguardando_redacao[user_id] = True
    │
    └─→ Próxima mensagem do usuário:
        │
        ├─→ Verifica se está aguardando redação
        │
        ├─→ Verifica limite novamente
        │
        ├─→ Processa correção
        │   └─→ RedacaoService.corrigir_redacao()
        │       ├─→ Monta prompt para OpenAI
        │       ├─→ Chama openai_client.chat.completions.create()
        │       └─→ Retorna feedback detalhado
        │
        ├─→ Envia feedback ao usuário
        │
        ├─→ Registra correção
        │   └─→ daily_limit_service.register_correction()
        │
        └─→ Remove de usuarios_aguardando_redacao
```

---

## 🏗️ Arquitetura de Componentes

### **1. Configuração (config.py)**

**Responsabilidades:**
- Tokens e credenciais (Telegram, OpenAI, Mercado Pago)
- IDs de grupos permitidos e administradores
- Palavras-chave de trigger
- System prompt para OpenAI
- Configuração de webhook (Ngrok URL, porta)

**Inicializa:**
- Bot do Telegram
- Dispatcher e Router
- Cliente OpenAI
- Serviço Mercado Pago

---

### **2. Handlers (handlers/message_handlers.py)**

**Funções principais:**
- `handle_message()` - Processa todas as mensagens recebidas
- `handle_gpt_command()` - Gerencia comando `/gpt`
- `check_payment_periodically()` - Verifica pagamentos em background
- `handle_confirm_payment_command()` - Comando admin para confirmar pagamento

**Segurança:**
- Links e códigos PIX só em conversas privadas
- Verificação de grupos permitidos
- Controle de limites diários

---

### **3. Serviços de Produtos (services/products_config.py)**

**Estrutura:**
```python
Product:
    - id: str
    - name: str
    - product_type: str
    - price: float
    - link: Optional[str]
    - description: Optional[str]
    - active: bool
```

**Funções:**
- `get_product(product_id)` - Busca produto por ID
- `get_product_by_type(type)` - Busca por tipo
- `update_product_price(id, price)` - Atualiza preço
- `add_product(product)` - Adiciona novo produto
- `deactivate_product(id)` - Desativa produto

**Benefícios:**
- Centralização de produtos e preços
- Facilita adição de novos produtos
- Facilita alteração de preços

---

### **4. Serviço de Pagamento (services/payment_service.py)**

**Responsabilidades:**
- Gerenciar usuários pagantes (`paid_users`)
- Gerenciar pagamentos pendentes (`pending_payments`)
- Verificar status de pagamentos via Mercado Pago
- Confirmar pagamentos e conceder acesso

**Persistência:**
- `data/paid_users.json` - Armazena usuários pagantes

**Funções principais:**
- `is_paid_user(user_id)` - Verifica se usuário pagou
- `register_pending_payment()` - Registra pagamento pendente
- `confirm_payment()` - Confirma pagamento e concede acesso
- `verify_payment_for_user()` - Verifica pagamento via API

---

### **5. Gerador de PIX (services/pix_generator.py)**

**Responsabilidades:**
- Gerar códigos PIX via Mercado Pago
- Mapear payment_id ↔ user_id
- Reutilizar pagamentos pendentes

**Persistência:**
- `data/pix_mappings.json` - Mapeamento de pagamentos

**Fluxo:**
1. Verifica se já existe pagamento pendente para o usuário
2. Se existe e está pendente: reutiliza
3. Se não existe: cria novo pagamento via Mercado Pago
4. Armazena mapeamento payment_id → user_id
5. Retorna: payment_id, pix_code, qr_code_base64

---

### **6. Serviço Mercado Pago (services/mercadopago_service.py)**

**Responsabilidades:**
- Integração com API do Mercado Pago
- Criar pagamentos PIX
- Consultar status de pagamentos
- Extrair informações de pagamento

**Funções principais:**
- `create_pix_payment()` - Cria pagamento PIX
- `get_payment_info()` - Obtém informações do pagamento
- `check_payment_status()` - Verifica status
- `extract_pix_code()` - Extrai código PIX
- `extract_pix_qr_code_base64()` - Extrai QR Code

---

### **7. Serviço GPT (services/gpt_service.py)**

**Responsabilidades:**
- Mensagens informativas sobre GPT Premium
- Mensagens de pagamento
- Mensagens de acesso (com link vitalício)

**Funções:**
- `get_gpt_info_message()` - Informações sobre o serviço
- `get_payment_message()` - Mensagem com código PIX
- `get_gpt_access_message()` - Mensagem com link vitalício

---

### **8. Serviço de Redação (services/redacao_service.py)**

**Responsabilidades:**
- Correção de redações usando OpenAI
- Aplicar metodologia ENEM
- Retornar notas e feedback

**Fluxo:**
1. Recebe texto da redação
2. Monta prompt com instruções ENEM
3. Chama OpenAI API (GPT-4)
4. Retorna feedback formatado

---

### **9. Controle de Limites (services/daily_limit_service.py)**

**Responsabilidades:**
- Controlar limite de 1 correção por dia por usuário
- Resetar contadores diariamente (meia-noite)
- Verificar se usuário pode fazer correção

**Estrutura:**
```python
user_limits = {
    user_id: {
        'count': int,
        'last_reset': datetime
    }
}
```

---

### **10. Propaganda (services/propaganda_service.py)**

**Responsabilidades:**
- Enviar propagandas diárias sobre GPT Premium
- Controlar envio (1 vez por dia)
- Enviar para todos os grupos permitidos

**Fluxo:**
- Scheduler verifica se já enviou hoje
- Se não: envia para todos os grupos permitidos
- Marca como enviado

---

### **11. Webhook (webhook/payment_webhook.py)**

**Responsabilidades:**
- Receber notificações do Mercado Pago
- Processar webhooks de pagamento
- Confirmar pagamentos automaticamente

**Endpoints:**
- `POST /webhook/payment` - Recebe webhooks
- `GET /health` - Health check

**Fluxo:**
1. Recebe webhook do Mercado Pago
2. Extrai payment_id
3. Consulta API para obter dados completos
4. Identifica user_id
5. Verifica status = 'approved'
6. Confirma pagamento
7. Envia link via mensagem privada

---

## 🔄 Fluxos de Dados

### **Fluxo de Dados - Pagamento**

```
Usuário → Bot → pix_generator → Mercado Pago API
                                    ↓
                            payment_id, pix_code
                                    ↓
                            payment_service (registra pendente)
                                    ↓
                            Usuário paga via PIX
                                    ↓
                            Mercado Pago → Webhook
                                    ↓
                            payment_webhook → payment_service
                                    ↓
                            Confirma pagamento → Envia link
```

### **Fluxo de Dados - Correção de Redação**

```
Usuário → Bot → daily_limit_service (verifica limite)
                                    ↓
                            RedacaoService → OpenAI API
                                    ↓
                            Feedback → Bot → Usuário
                                    ↓
                            daily_limit_service (registra correção)
```

---

## 🔐 Segurança e Validações

### **Validações de Segurança:**

1. **Links e Códigos PIX:**
   - ✅ Nunca enviados em grupos
   - ✅ Sempre via mensagem privada
   - ✅ Verificação de tipo de chat antes de enviar

2. **Grupos Permitidos:**
   - ✅ Bot só responde em grupos configurados
   - ✅ Mensagens de grupos não permitidos são ignoradas

3. **Limites Diários:**
   - ✅ 1 correção gratuita por dia por usuário
   - ✅ Reset automático à meia-noite

4. **Comandos Administrativos:**
   - ✅ Apenas ADMIN_IDS podem usar /confirmar_pagamento

5. **Pagamentos:**
   - ✅ Verificação de valor mínimo
   - ✅ Verificação de status na API do Mercado Pago
   - ✅ Mapeamento seguro payment_id ↔ user_id

---

## 📊 Persistência de Dados

### **Arquivos JSON:**

1. **data/paid_users.json**
```json
{
  "paid_users": [user_id1, user_id2, ...],
  "pending_payments": {
    "user_id": {
      "timestamp": "2024-01-01T00:00:00",
      "amount": 50.0,
      "payment_reference": "payment_id",
      "pix_code": "...",
      "product_id": "gpt_premium"
    }
  }
}
```

2. **data/pix_mappings.json**
```json
{
  "payment_to_user": {
    "payment_id": user_id
  },
  "user_to_payment": {
    "user_id": "payment_id"
  }
}
```

---

## 🎯 Pontos de Extensão

### **Para Adicionar Novo Produto:**

1. Editar `services/products_config.py`
2. Adicionar novo `Product` ao dicionário `PRODUCTS`
3. Usar `product_id` nas funções de pagamento

### **Para Adicionar Novo Handler:**

1. Criar função em `handlers/message_handlers.py`
2. Adicionar lógica em `handle_message()`
3. Registrar no router (já está configurado)

### **Para Modificar Preço:**

1. Editar `services/products_config.py`
2. Alterar `price` do produto
3. Ou usar `update_product_price(product_id, new_price)`

---

## 📝 Notas Importantes

- **Polling vs Webhook:** O bot usa polling para mensagens do Telegram
- **Webhook:** Usado apenas para receber notificações do Mercado Pago
- **Background Tasks:** Verificação de pagamento e propagandas rodam em background
- **Privacidade:** Informações sensíveis sempre via mensagem privada
- **Fallback:** Verificação periódica garante confirmação mesmo se webhook falhar

---

## 🔧 Dependências Principais

- `aiogram` - Framework do Telegram Bot
- `openai` - API da OpenAI
- `aiohttp` - Servidor webhook assíncrono
- `python-dotenv` - Variáveis de ambiente

---

## 📈 Melhorias Futuras Sugeridas

1. Migrar tokens para variáveis de ambiente (.env)
2. Implementar validação de assinatura de webhook
3. Adicionar mais produtos (redação avulsa, etc.)
4. Implementar sistema de cronograma completo
5. Adicionar métricas e analytics
6. Implementar sistema de notificações
7. Adicionar testes automatizados

