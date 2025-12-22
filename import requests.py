import requests
import json

def test_ollama_connection():
    try:
        # Teste básico de conexão
        response = requests.get('http://127.0.0.1:11434/api/generate')
        print(f"Versão do Ollama: {response.json()}")
        
        # Teste do modelo
        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                "model": "deepseek-r1:7b",
                "prompt": "Teste de conexão",
                "stream": False
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.json()}")
        
    except requests.exceptions.ConnectionError:
        print("Erro de conexão: Não foi possível conectar ao servidor Ollama")
    except Exception as e:
        print(f"Erro: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    test_ollama_connection()