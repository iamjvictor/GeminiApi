import os # Módulo para interagir com o sistema operacional, como verificar se um arquivo existe.
import PyPDF2 # Biblioteca para ler e extrair texto de arquivos PDF.
import numpy as np # Biblioteca para computação numérica, usada aqui para cálculos de similaridade vetorial.

from dotenv import load_dotenv # Função para carregar variáveis de ambiente de um arquivo .env.
import google.generativeai as genai # Biblioteca do Google para interagir com os modelos de IA generativa (Gemini).


load_dotenv() # Carrega as variáveis de ambiente definidas no arquivo .env para o ambiente atual.
api_key = os.getenv('GOOGLE_API_KEY') # Obtém o valor da variável de ambiente 'GOOGLE_API_KEY'.


genai.configure(api_key=api_key) # Configura a biblioteca do Google AI com a chave da API fornecida.
# modelList =  genai.list_models() # Linha comentada: Listaria todos os modelos disponíveis (não usada no fluxo atual).

# model = "gemini-2.0-flash" # Linha comentada: Definiria o nome de um modelo específico (não usada no fluxo atual).
# generative_model_instance = genai.GenerativeModel(model) # Linha comentada: Instanciaria um modelo generativo (não usada no fluxo atual).

def extract_text_from_file(json_data):
    """Extrai texto de dados JSON que contêm o texto completo do PDF."""
    print(f"Extraindo texto de dados JSON")
    text = ""
    
    try:
        # Verifica se json_data é um dicionário (JSON parseado)
        if isinstance(json_data, dict):
            # Assumindo que o texto está em uma chave específica, como 'text' ou 'content'
            # Você pode ajustar a chave conforme a estrutura do seu JSON
            if 'text' in json_data:
                text = json_data['text']
            elif 'content' in json_data:
                text = json_data['content']
            elif 'pdf_text' in json_data:
                text = json_data['pdf_text']
            else:
                # Se não encontrar uma chave específica, tenta usar todo o conteúdo
                # Assumindo que o JSON contém o texto diretamente
                text = str(json_data)
        elif isinstance(json_data, str):
            # Se for uma string JSON, tenta fazer o parse
            import json
            parsed_data = json.loads(json_data)
            if isinstance(parsed_data, dict):
                if 'text' in parsed_data:
                    text = parsed_data['text']
                elif 'content' in parsed_data:
                    text = parsed_data['content']
                elif 'pdf_text' in parsed_data:
                    text = parsed_data['pdf_text']
                else:
                    text = str(parsed_data)
            else:
                text = str(parsed_data)
        else:
            # Se não for dict nem string, converte para string
            text = str(json_data)
            
        if not text or not text.strip():
            print("AVISO: Nenhum texto encontrado nos dados JSON")
            return ""
            
        print(f"Texto extraído com sucesso. Tamanho: {len(text)} caracteres")
        return text
        
    except Exception as e:
        print(f"ERRO ao processar dados JSON: {e}")
        return ""
    """Extrai texto de arquivos PDF ou TXT."""
    print(f"Extraindo texto de: {file_path}") # Imprime uma mensagem indicando qual arquivo está sendo processado.
    text = "" # Inicializa uma string vazia para armazenar o texto extraído.
    _, file_extension = os.path.splitext(file_path) # Obtém a extensão do arquivo.

    try: # Inicia um bloco try-except para tratamento de possíveis erros durante a leitura do PDF.
        if file_extension.lower() == '.pdf':
            with open(file_path, 'rb') as file: # Abre o arquivo PDF no modo de leitura binária ('rb').
                reader = PyPDF2.PdfReader(file) # Cria um objeto PdfReader para ler o conteúdo do PDF.
                print(f"Número de páginas: {len(reader.pages)}") # Imprime o número de páginas do PDF.
                
                if reader.is_encrypted: # Verifica se o PDF está criptografado.
                     print(f"AVISO: O arquivo {file_path} está criptografado e não pode ser lido.") # Informa se o PDF está criptografado.
                     return "" # Retorna uma string vazia se o PDF estiver criptografado.
                for page_num in range(len(reader.pages)): # Itera sobre cada página do PDF.
                    page = reader.pages[page_num] # Obtém o objeto da página atual.
                    
                    text += page.extract_text() or "" # Extrai o texto da página e o adiciona à variável 'text'. O 'or ""' garante que, se extract_text() retornar None, uma string vazia seja adicionada.
        elif file_extension.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file: # Abre o arquivo de texto no modo de leitura.
                text = file.read()
        else:
            print(f"AVISO: Formato de arquivo não suportado para {file_path}. Apenas .pdf e .txt são aceitos.")
            return ""
    except FileNotFoundError: # Captura o erro se o arquivo PDF não for encontrado.
        print(f"ERRO: Arquivo não encontrado: {file_path}") # Imprime uma mensagem de erro.
        return "" # Retorna uma string vazia.
    except Exception as e: # Captura qualquer outra exceção que possa ocorrer durante a leitura.
        print(f"ERRO ao ler o arquivo {file_path}: {e}") # Imprime a mensagem de erro específica.
        return "" # Retorna uma string vazia.
    return text # Retorna o texto completo extraído do PDF.


def get_text_chunks(text, chunk_size=1000, chunk_overlap=200):
    # Define o tamanho padrão dos chunks e a sobreposição.
    if not text or not text.strip(): # Verifica se o texto de entrada está vazio ou contém apenas espaços em branco.
        print("Texto de entrada está vazio. Nenhum chunk gerado.") # Informa que nenhum chunk será gerado.
        return [] # Retorna uma lista vazia.
        
    chunks = [] # Inicializa uma lista vazia para armazenar os chunks de texto.
    start_index = 0 # Define o índice inicial para o primeiro chunk.
    while start_index < len(text): # Continua enquanto o índice inicial for menor que o comprimento total do texto.
        end_index = start_index + chunk_size # Calcula o índice final do chunk atual.
        chunks.append(text[start_index:end_index]) # Adiciona o pedaço de texto (chunk) à lista de chunks.
        start_index += chunk_size - chunk_overlap # Atualiza o índice inicial para o próximo chunk, considerando a sobreposição.
        if end_index >= len(text): # Verifica se o índice final ultrapassou o final do texto.
            break # Interrompe o loop se o final do texto foi alcançado.
    return [chunk for chunk in chunks if chunk.strip()] # Retorna a lista de chunks, removendo quaisquer chunks que sejam apenas espaços em branco.

def generate_embeddings(text_chunks, task_type="RETRIEVAL_DOCUMENT"):
    """Gera embeddings para uma lista de pedaços de texto."""
    # O task_type padrão é para documentos que serão armazenados e pesquisados.
    print(f"\nGerando embeddings para {len(text_chunks)} chunks (task: {task_type})...") # Informa o início do processo de geração de embeddings.
    if not text_chunks: # Verifica se a lista de chunks está vazia.
        print("Nenhum chunk fornecido para gerar embeddings.") # Informa que não há chunks para processar.
        return [] # Retorna uma lista vazia.

    embeddings = [] # Inicializa uma lista vazia para armazenar os vetores de embedding.
    embedding_model = "models/text-embedding-004" # Define o nome do modelo de embedding a ser usado.
    
    for i, chunk in enumerate(text_chunks): # Itera sobre cada chunk de texto com seu índice.
        if not chunk.strip(): # Verifica se o chunk atual está vazio ou contém apenas espaços.
            print(f"Chunk {i+1} está vazio, pulando a geração de embedding.") # Informa que o chunk está sendo pulado.
            continue # Pula para o próximo chunk.
        try: # Inicia um bloco try-except para tratamento de erros durante a chamada da API de embedding.
            # print(f"Gerando embedding para o chunk {i+1}/{len(text_chunks)}: '{chunk[:50]}...'")
            result = genai.embed_content( # Chama a API do Google para gerar o embedding.
                model=embedding_model, # Especifica o modelo de embedding.
                content=chunk, # Fornece o texto do chunk.
                task_type=task_type # Especifica o tipo de tarefa (documento ou consulta) para otimizar o embedding.
            )
            embeddings.append(result['embedding']) # Adiciona o vetor de embedding resultante à lista.
        except Exception as e: # Captura qualquer exceção durante a geração do embedding.
            print(f"ERRO ao gerar embedding para o chunk {i+1} ('{chunk[:50]}...'): {e}") # Imprime a mensagem de erro.
    return embeddings # Retorna a lista de vetores de embedding.


def find_most_relevant_chunks(query_embedding, doc_embeddings, doc_chunks, top_k=3):
    """Encontra os chunks mais relevantes baseados na similaridade de cosseno."""
    # top_k define quantos dos chunks mais similares serão retornados.
    print(f"\nEncontrando os {top_k} chunks mais relevantes...") # Informa o início da busca por chunks relevantes.
    if not doc_embeddings or not query_embedding or not doc_chunks: # Verifica se todas as entradas necessárias foram fornecidas.
        print("Dados de entrada insuficientes para encontrar chunks relevantes.") # Informa sobre dados insuficientes.
        return [] # Retorna uma lista vazia.
    
    query_embedding_np = np.array(query_embedding) # Converte o embedding da consulta para um array NumPy.
    doc_embeddings_np = np.array(doc_embeddings) # Converte a lista de embeddings dos documentos para um array NumPy.

    # Calcula a similaridade de cosseno entre o embedding da consulta e todos os embeddings dos documentos.
    # A fórmula é: similaridade = (A . B) / (||A|| * ||B||)
    dot_products = np.dot(doc_embeddings_np, query_embedding_np) # Calcula o produto escalar entre os vetores.
    norm_query = np.linalg.norm(query_embedding_np) # Calcula a norma (magnitude) do vetor de embedding da consulta.
    norm_docs = np.linalg.norm(doc_embeddings_np, axis=1) # Calcula a norma de cada vetor de embedding dos documentos.
    
    similarities = dot_products / (norm_docs * norm_query) # Calcula a similaridade de cosseno.
    
    top_k_indices = np.argsort(similarities)[-top_k:][::-1] # Obtém os índices dos 'top_k' chunks mais similares, ordenados do mais similar para o menos.
    return [(doc_chunks[i], similarities[i]) for i in top_k_indices if i < len(doc_chunks)] # Retorna uma lista de tuplas, cada uma contendo o texto do chunk e sua pontuação de similaridade.


def find_relevant_chunks_from_json(json_data, user_query, top_k=3):
    """
    Função que recebe um JSON com texto e uma pergunta do usuário,
    retorna os chunks mais relevantes para análise pela IA.
    
    Args:
        json_data (dict): JSON contendo o texto a ser processado
        user_query (str): Pergunta do usuário
        top_k (int): Número de chunks mais relevantes a retornar
    
    Returns:
        list: Lista de tuplas (chunk, score) com os chunks mais relevantes
    """
    # Extrai o texto do JSON (assumindo que o texto está em uma chave 'text' ou 'content')
    all_text = json_data.get('text', '') or json_data.get('content', '')
    
    if not all_text:
        print("AVISO: Nenhum texto encontrado no JSON fornecido.")
        return []
    
    # Divide o texto em chunks
    document_chunks = get_text_chunks(all_text)
    
    # Gera embeddings para os chunks dos documentos
    document_embeddings = generate_embeddings(document_chunks)
    
    if not document_embeddings:
        print("ERRO: Não foi possível gerar embeddings para os documentos.")
        return []
    
    # Gera embedding para a pergunta do usuário
    query_embedding_list = generate_embeddings([user_query], task_type="RETRIEVAL_QUERY")
    
    if not query_embedding_list:
        print("ERRO: Não foi possível gerar embedding para a pergunta.")
        return []
    
    query_embedding = query_embedding_list[0]
    
    # Encontra os chunks mais relevantes
    relevant_chunks_with_scores = find_most_relevant_chunks(
        query_embedding, 
        document_embeddings, 
        document_chunks, 
        top_k=top_k
    )
    
    return relevant_chunks_with_scores

