# Webhook de Pagamento

Este módulo gerencia o recebimento de notificações de pagamento via webhook.

## Configuração

### 1. Ngrok
O túnel ngrok já está configurado: `https://b597ffb1a237.ngrok-free.app`

### 2. Endpoints Disponíveis

- **Webhook de Pagamento:** `POST /webhook/payment` ou `POST /payment`
- **Health Check:** `GET /health` ou `GET /`

### 3. Configuração no Provedor de Pagamento

Configure o webhook no seu provedor de pagamento (Mercado Pago, PagSeguro, etc.) para enviar notificações para:

```
https://b597ffb1a237.ngrok-free.app/webhook/payment
```

### 4. Formato Esperado do Webhook

O webhook aceita diferentes formatos. O sistema tenta extrair:

- **user_id**: Do campo `metadata.user_id`, `custom_data.user_id`, ou da descrição/referência no formato `user_123456789`
- **amount**: Valor do pagamento (deve ser >= 50.0)
- **status**: Status do pagamento (deve ser: 'paid', 'approved', 'completed', 'pago')

#### Exemplo de Payload Esperado:

```json
{
  "type": "payment",
  "data": {
    "user_id": 123456789,
    "amount": 50.0,
    "status": "paid",
    "metadata": {
      "user_id": 123456789
    }
  }
}
```

Ou:

```json
{
  "event": "payment.received",
  "data": {
    "description": "user_123456789",
    "value": 50.0,
    "status": "approved"
  }
}
```

### 5. Fluxo de Processamento

1. Usuário digita `/GPT` no bot
2. Bot envia chave PIX e instruções
3. Usuário faz pagamento incluindo `user_{user_id}` na referência
4. Provedor de pagamento envia webhook para o ngrok
5. Sistema processa webhook e confirma pagamento
6. Bot envia link do GPT automaticamente ao usuário

### 6. Validação de Segurança

⚠️ **IMPORTANTE:** Atualmente a validação de assinatura está desabilitada. 

Para produção, implemente a validação de assinatura no método `validate_webhook_signature()` em `payment_webhook.py` conforme a documentação do seu provedor de pagamento.

### 7. Testando o Webhook

Você pode testar o webhook usando curl:

```bash
curl -X POST https://b597ffb1a237.ngrok-free.app/webhook/payment \
  -H "Content-Type: application/json" \
  -d '{
    "type": "payment",
    "data": {
      "user_id": 123456789,
      "amount": 50.0,
      "status": "paid"
    }
  }'
```

Ou testar o health check:

```bash
curl https://b597ffb1a237.ngrok-free.app/health
```




