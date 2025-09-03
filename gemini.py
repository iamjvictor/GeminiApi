from dotenv import load_dotenv # Função para carregar variáveis de ambiente de um arquivo .env.
import google.generativeai as genai # Biblioteca do Google para interagir com os modelos de IA generativa (Gemini).
import os

load_dotenv() # Carrega as variáveis de ambiente definidas no arquivo .env para o ambiente atual.
api_key = os.getenv('GOOGLE_API_KEY') # Obtém o valor da variável de ambiente 'GOOGLE_API_KEY'.


genai.configure(api_key=api_key) # Configura a biblioteca do Google AI com a chave da API fornecida.
# modelList =  genai.list_models() # Linha comentada: Listaria todos os modelos disponíveis (não usada no fluxo atual).

model = "gemini-2.0-flash" # Linha comentada: Definiria o nome de um modelo específico (não usada no fluxo atual).
generative_model_instance = genai.GenerativeModel(model) # Linha comentada: Instanciaria um modelo generativo (não usada no fluxo atual).
def generate_response_with_gemini(relevant_chunks, user_question, chat_history=""):
    """
    Gera uma resposta usando o modelo Gemini baseada nos chunks relevantes e na pergunta do usuário.
    
    Args:
        relevant_chunks (list): Lista de tuplas (chunk, score) com os chunks mais relevantes
        user_question (str): Pergunta do usuário
        chat_history (str): Histórico da conversa anterior (opcional)
    
    Returns:
        str: Resposta gerada pelo modelo Gemini
    """
    if not relevant_chunks:
        return "Desculpe, não encontrei informações relevantes para responder sua pergunta."
    
    # Prepara o contexto combinando os chunks relevantes
    context = "\n\n".join([chunk for chunk, score in relevant_chunks])
    
    # Cria o prompt para o modelo
    prompt = f"""
    ### PERSONA E MISSÃO PRINCIPAL ###
        Você é o "Victor", o Recepcionista Virtual da Pousada Sol & Mar em Cabo Frio. Sua personalidade é proativa, extremamente prestativa, amigável e com um tom leve e solar. Sua missão é garantir que cada hóspede se sinta bem-vindo e tenha suas dúvidas resolvidas da forma mais humana e eficiente possível.

        ### REGRAS DE OURO DA CONVERSA (CRÍTICO) ###
        0.  **Regra de Saudação Condicional (A MAIS IMPORTANTE):**
            * **SE** o [HISTÓRICO DA CONVERSA] abaixo estiver **VAZIO**, esta é a primeira interação do dia. Comece com uma saudação calorosa e apropriada para o horário (ex: "Olá, bom dia! Sou o Leo, seu assistente virtual da Pousada Sol & Mar. Como posso te ajudar hoje?").
            * **SE** o [HISTÓRICO DA CONVERSA] **JÁ CONTIVER MENSAGENS**, a conversa já está em andamento. **NÃO USE UMA NOVA SAUDAÇÃO.** Vá direto ao ponto, respondendo à nova pergunta do usuário de forma natural e contextual.

        1.  **A Fonte da Verdade para Fatos:** Para perguntas sobre regras e serviços da pousada, sua ÚNICA fonte de verdade é o [CONTEXTO]. NUNCA invente horários, preços ou regras.

        2.  **O Detetive Amigável (Perguntas Ambíguas):** Se uma pergunta for vaga (ex: "e o lazer?"), faça perguntas para entender melhor o que o usuário quer saber. ("Claro! Você gostaria de saber sobre as opções de lazer aqui na pousada, ou dicas de passeios em Cabo Frio?")

        3.  **O Assistente Proativo (Informação Fora do Contexto):** Se a resposta para uma pergunta factual NÃO estiver no [CONTEXTO], JAMAIS diga apenas "não sei". Siga o roteiro:
            * a. **Seja transparente:** "Ótima pergunta! Eu verifiquei aqui e não tenho essa informação específica."
            * b. **Ofereça uma solução alternativa:** "Mas posso verificar com a equipe e te retorno em breve, ou posso te passar o contato de um parceiro que pode ajudar. O que prefere?"
            * c. **Sugira contato humano como último recurso:** "Se o assunto for urgente, posso pedir para um de nossos recepcionistas te ligar."

        4.  **Conversa Livre e Empatia:** Você TEM permissão para conversar sobre assuntos gerais para criar conexão (tempo, dicas de praias, etc.), usando seu conhecimento geral.

        ---
        [CONTEXTO DO HOTEL]
        {context}
        ---
        [HISTÓRICO DA CONVERSA RECENTE]
        {chat_history}
        ---
        [NOVA PERGUNTA DO USUÁRIO]
        {user_question}
        ---
    """
        
    try:
        # Gera a resposta usando o modelo Gemini
        response = generative_model_instance.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar resposta com Gemini: {e}")
        return "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."



def process_google_event(payload: dict) -> dict:
    """
    Processa o evento recebido do Google Calendar e gera uma resposta usando o modelo Gemini.
    
    Args:
        promptPayload (dict): Payload do evento do Google Calendar
    
    Returns:
        dict: Resposta gerada pelo modelo Gemini
    """
    try:
       # Extrai os dados do payload recebido do seu backend Node.js
            event = payload.get('event', {})
            user = payload.get('user', {})
            available_rooms = user.get('availableRooms', [])

            # 1. MONTAGEM DO PROMPT PARA A IA
            # Este prompt é a "alma" da sua lógica de tradução.
            prompt = f"""
            Você é um assistente especialista em processar dados de reservas de hotel para um sistema de automação.
            Analise os dados de um evento do Google Calendar e a lista de quartos disponíveis para extrair informações em um formato JSON específico.

            **Dados do Evento Recebido:**
            - Título (summary): "{event.get('summary', '')}"
            - Descrição (description): "{event.get('description', '')}"
            - Data de Início: "{event.get('start', '')}"
            - Data de Fim: "{event.get('end', '')}"

            **Lista de Nomes de Quartos Válidos neste Hotel:**
            - {', '.join(available_rooms)}

            **Sua Tarefa:**
            Baseado nos dados acima, retorne um objeto JSON contendo as seguintes chaves. Se uma informação não puder ser extraída, retorne null para o campo correspondente.
            1.  "roomName": A partir do Título do evento, identifique o nome do quarto mais provável da lista de quartos válidos.
            2.  "leadName": A partir da Descrição ou do Título, extraia o nome completo do hóspede.
            3.  "leadEmail": Extraia o endereço de e-mail do hóspede da Descrição.
            4.  "leadWhatsapp": Extraia um número de telefone no formato WhatsApp (apenas dígitos) da Descrição.
            
            Responda APENAS com o objeto JSON. Não inclua texto adicional ou formatação.
            Exemplo de resposta:
            {{
            "roomName": "Suíte Master",
            "leadName": "Ana Clara Medeiros",
            "leadEmail": "anaclara.medeiros@example.com",
            "leadWhatsapp": "5521987654321"
            }}
            """

            print("--- PROMPT ENVIADO PARA A IA ---")
            print(prompt)
            print("-------------------------------")

            response = generative_model_instance.generate_content(prompt)
            # Limpa a resposta para garantir que seja um JSON válido
                cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
                
                print("--- RESPOSTA DA IA (JSON Mastigado) ---")
                print(cleaned_response_text)
                print("--------------------------------------")
                
                # 3. CONVERTE A RESPOSTA DE TEXTO PARA UM DICIONÁRIO PYTHON
                processed_data = json.loads(cleaned_response_text)
                return processed_data
    except Exception as e:
        print(f"Erro ao processar evento do Google Calendar: {e}")
        return {
            "response_gemini": "Desculpe, ocorreu um erro ao processar o evento. Tente novamente."
        }
    
    