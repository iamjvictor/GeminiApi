# generateChunks.py

import numpy as np
import google.generativeai as genai

# ==============================================================================
#  FUNÇÕES DE SUPORTE (O MOTOR DA FÁBRICA)
# ==============================================================================

def get_text_chunks(text: str, chunk_size=1000, chunk_overlap=200) -> list[str]:
    """Divide um texto longo em pedaços (chunks) menores e sobrepostos."""
    if not text or not text.strip():
        print("AVISO: Texto de entrada para chunking está vazio.")
        return []
        
    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        chunks.append(text[start_index:end_index])
        start_index += chunk_size - chunk_overlap
    
    return [chunk for chunk in chunks if chunk.strip()]

def generate_embeddings(text_chunks: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Gera embeddings para uma lista de textos usando a API do Google."""
    print(f"Gerando embeddings para {len(text_chunks)} chunks (tarefa: {task_type})...")
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
        print(f"ERRO ao gerar embeddings: {e}")
        # Lança o erro para a camada superior tratar
        raise e

# ==============================================================================
#  FUNÇÃO PRINCIPAL (O PRODUTO FINAL DA FÁBRICA)
# ==============================================================================

def generate_vectorized_chunks(full_text: str) -> list[dict]:
    """
    Orquestra o processo completo de chunking e embedding.
    Recebe um texto e retorna uma lista de dicionários com os chunks e seus vetores.
    """
    if not full_text.strip():
        raise ValueError("O texto do documento está vazio ou inválido.")

    # 1. Dividir em pedaços
    chunks = get_text_chunks(full_text)
    if not chunks:
        raise ValueError("Não foi possível gerar chunks a partir do texto.")

    # 2. Criar os vetores (embeddings)
    embeddings = generate_embeddings(chunks)
    if not embeddings or len(chunks) != len(embeddings):
        raise RuntimeError("Falha ao gerar embeddings ou incompatibilidade de tamanho.")

    # 3. Montar a resposta final
    vectorized_chunks = [
        {"content": chunk, "embedding": embedding}
        for chunk, embedding in zip(chunks, embeddings)
    ]
    
    print(f"✅ Indexação concluída. Retornando {len(vectorized_chunks)} chunks com embeddings.")
    return vectorized_chunks