# rag_pipeline.py (versão otimizada)

import os
import requests  # Para fazer a chamada HTTP para o seu backend Node.js
import google.generativeai as genai

# ==============================================================================
#  MODIFICAÇÃO 1: REMOÇÃO DE FUNÇÕES DESNECESSÁRIAS
#  As funções get_text_chunks e find_most_relevant_chunks não são mais
#  necessárias AQUI. O chunking agora acontece na "fábrica" (generateChunks.py)
#  e a busca por similaridade acontece no banco de dados.
# ==============================================================================

# A função generate_embeddings ainda é necessária, mas apenas para a pergunta do usuário.
def generate_embeddings(text_chunks: list[str], task_type: str) -> list[list[float]]:
    """Gera embeddings para uma lista de textos (agora usada apenas para a pergunta)."""
    print(f"Gerando embedding para 1 chunk (tarefa: {task_type})...")
    if not text_chunks:
        return []

    embedding_model = "models/text-embedding-004"
    try:
        result = genai.embed_content(
            model=embedding_model,
            content=text_chunks,
            task_type=task_type
        )
        return result['embedding']
    except Exception as e:
        print(f"ERRO ao gerar embedding para a pergunta: {e}")
        raise e # Lança o erro para a camada superior tratar

# ==============================================================================
#  MODIFICAÇÃO 2: A NOVA FUNÇÃO PRINCIPAL (O ORQUESTRADOR DA BUSCA)
#  Esta função foi completamente reescrita. Ela não processa mais o documento,
#  ela orquestra a busca rápida dos chunks que já estão processados no banco.
# ==============================================================================

def process_rag_pipeline(user_id: str, user_question: str) -> str:
    """
    Orquestra o processo de RAG otimizado:
    1. Gera o embedding da pergunta do usuário.
    2. Busca os chunks pré-vetorizados mais relevantes no banco de dados (via Gateway Node.js).
    3. Retorna o contexto final para o prompt do Gemini.

    Args:
        user_id (str): ID do usuário para filtrar os documentos no banco.
        user_question (str): A pergunta do usuário.

    Returns:
        str: Uma string única contendo o contexto dos chunks mais relevantes.
    """
    print("🚀 Iniciando pipeline de RAG (busca rápida no banco)...")
    
    # Passo 1: Gerar o embedding APENAS para a pergunta do usuário.
    query_embedding_list = generate_embeddings([user_question], task_type="RETRIEVAL_QUERY")
    if not query_embedding_list:
        print("ERRO: Não foi possível gerar embedding para a pergunta.")
        return ""
    query_embedding = query_embedding_list[0]

    # Passo 2: Chamar seu Gateway Node.js para que ele faça a busca vetorial no Supabase.
    print("📡 Chamando Gateway para busca de chunks por similaridade...")
    try:
        gateway_api_url = os.getenv("BACKEND_URL")
        if not gateway_api_url:
            raise ValueError("Variável de ambiente BACKEND_URL não configurada.")
        
        # O payload para a requisição ao seu novo endpoint Node.js
        payload = {
            "user_id": user_id,
            "query_embedding": query_embedding,
            "top_k": 3 # O número de chunks que você quer de volta
        }
        
        # Headers de autenticação para seu middleware no Node.js
        auth_headers = {
            'x-user-id': user_id,
            'x-api-key': os.getenv("API_SECRET_KEY")
        }

        # Faz a chamada POST para o novo endpoint que você criou no Node.js
        response = requests.post(
            f"{gateway_api_url}/document-chunks/find-relevant",
            json=payload,
            headers=auth_headers
        )
        response.raise_for_status() # Lança um erro se a resposta for 4xx ou 5xx

        # A resposta do Node.js conterá os textos dos chunks mais relevantes
        relevant_chunks = response.json().get('data', [])

    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO ao comunicar com o Gateway Node.js: {e}")
        return "Desculpe, não consegui buscar informações relevantes no momento."
    except Exception as e:
        print(f"❌ ERRO inesperado na busca de chunks: {e}")
        return "Desculpe, ocorreu um problema interno ao buscar informações."

    # Passo 3: Formatar o contexto final para o prompt do Gemini
    if not relevant_chunks:
        print("AVISO: Nenhuma informação relevante encontrada no banco de dados para esta pergunta.")
        return ""
        
    final_context = "\n\n---\n\n".join(relevant_chunks)
    print("✅ Contexto de RAG (via busca no banco) finalizado e pronto para o prompt.")
    
    return final_context