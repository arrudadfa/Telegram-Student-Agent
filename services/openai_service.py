from typing import List
from config import openai_client, logger, SYSTEM_PROMPT

async def get_openai_response(prompt: str) -> List[str]:
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            presence_penalty=0.6,
            frequency_penalty=0.2
        )
        
        if response and response.choices:
            full_response = response.choices[0].message.content.strip()
            
            # Adiciona log para debug
            logger.info(f"Resposta OpenAI recebida: {full_response[:100]}...")
            
            # Divide a resposta em partes se necessário
            if len(full_response) > 4000:
                return [full_response[i:i+4000] for i in range(0, len(full_response), 4000)]
            return [full_response]
            
    except Exception as e:
        logger.error(f"Erro na API OpenAI: {str(e)}")
        return ["Desculpe, ocorreu um erro ao processar sua mensagem."] 