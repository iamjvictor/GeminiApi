from dotenv import load_dotenv # Função para carregar variáveis de ambiente de um arquivo .env.
import google.generativeai as genai # Biblioteca do Google para interagir com os modelos de IA generativa (Gemini).
import os

load_dotenv() # Carrega as variáveis de ambiente definidas no arquivo .env para o ambiente atual.
api_key = os.getenv('GOOGLE_API_KEY') # Obtém o valor da variável de ambiente 'GOOGLE_API_KEY'.


genai.configure(api_key=api_key) # Configura a biblioteca do Google AI com a chave da API fornecida.
# modelList =  genai.list_models() # Linha comentada: Listaria todos os modelos disponíveis (não usada no fluxo atual).

model = "gemini-2.0-flash" # Linha comentada: Definiria o nome de um modelo específico (não usada no fluxo atual).
generative_model_instance = genai.GenerativeModel(model) # Linha comentada: Instanciaria um modelo generativo (não usada no fluxo atual).
def generate_response_with_gemini(relevant_chunks, user_question):
    """
    Gera uma resposta usando o modelo Gemini baseada nos chunks relevantes e na pergunta do usuário.
    
    Args:
        relevant_chunks (list): Lista de tuplas (chunk, score) com os chunks mais relevantes
        user_question (str): Pergunta do usuário
    
    Returns:
        str: Resposta gerada pelo modelo Gemini
    """
    if not relevant_chunks:
        return "Desculpe, não encontrei informações relevantes para responder sua pergunta."
    
    # Prepara o contexto combinando os chunks relevantes
    context = "\n\n".join([chunk for chunk, score in relevant_chunks])
    
    # Cria o prompt para o modelo
    prompt = f"""
    ### INSTRUÇÕES ###
    1.  **PERSONA:** Você é um assistente virtual com a personalidade de um surfista gente boa. Seja sempre amigável, use uma linguagem jovem e informal.
    2.  **SAUDAÇÃO:** Sempre, sem exceção, comece TODAS as suas respostas com "Aloha!".
    3.  **FONTE DA VERDADE:** Responda a pergunta do usuário usando APENAS as informações do CONTEXTO abaixo. Não use nenhum conhecimento externo.
    4.  **RESPOSTA NÃO ENCONTRADA:** Se a resposta para a pergunta não estiver claramente no CONTEXTO, responda que você não tem essa informação de uma forma amigável, como "Opa, essa informação eu não tenho aqui, demorô?".
    5.  **GÍRIAS:** Pode usar gírias como "show", "demorô", "na moral", "valeu".

    ### CONTEXTO ###
    {context}

    ### PERGUNTA DO USUÁRIO ###
    {user_question}
    """
        
    try:
        # Gera a resposta usando o modelo Gemini
        response = generative_model_instance.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar resposta com Gemini: {e}")
        return "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."
