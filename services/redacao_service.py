from typing import Dict, Tuple, Optional
from config import logger, openai_client, REDACAO_SYSTEM_PROMPT

class RedacaoService:
    @staticmethod
    async def corrigir_redacao(texto: str) -> Tuple[Optional[Dict[str, int]], str]:
        """
        Corrige uma redação usando os critérios do ENEM
        Returns: (notas por competência, feedback detalhado)
        """
        try:
            # Prompt específico para correção de redação
            prompt_correcao = f"""Corrija esta redação seguindo rigorosamente a metodologia da matriz de competências do ENEM:

{texto}

Por favor, forneça:
1. Nota de 0 a 200 para cada uma das 5 competências
2. Feedback detalhado sobre cada competência
3. Nota final total (soma das 5 competências)
4. Comentários gerais e sugestões de melhoria

Formate sua resposta de forma clara e organizada."""

            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": REDACAO_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_correcao}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            if response and response.choices:
                feedback = response.choices[0].message.content.strip()
                
                # Tenta extrair notas da resposta (opcional, para estrutura futura)
                notas = {
                    "comp1": 0, "comp2": 0, "comp3": 0,
                    "comp4": 0, "comp5": 0
                }
                
                logger.info(f"Redação corrigida com sucesso")
                return notas, feedback
            else:
                return None, "Erro: Não foi possível obter resposta do GPT"
            
        except Exception as e:
            logger.error(f"Erro ao corrigir redação: {e}")
            return None, f"Erro ao processar a correção: {str(e)}" 