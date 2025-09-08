from dotenv import load_dotenv # Função para carregar variáveis de ambiente de um arquivo .env.
import google.generativeai as genai # Biblioteca do Google para interagir com os modelos de IA generativa (Gemini).
import os
import json

load_dotenv() # Carrega as variáveis de ambiente definidas no arquivo .env para o ambiente atual.
api_key = os.getenv('GOOGLE_API_KEY') # Obtém o valor da variável de ambiente 'GOOGLE_API_KEY'.


genai.configure(api_key=api_key) # Configura a biblioteca do Google AI com a chave da API fornecida.
# modelList =  genai.list_models() # Linha comentada: Listaria todos os modelos disponíveis (não usada no fluxo atual).

model = "gemini-2.0-flash" # Linha comentada: Definiria o nome de um modelo específico (não usada no fluxo atual).
generative_model_instance = genai.GenerativeModel(model) # Linha comentada: Instanciaria um modelo generativo (não usada no fluxo atual).

def generate_response_with_gemini(rag_context: str, user_question: str, chat_history: str, knowledge: dict):

    # Monta o prompt final com todos os contextos
    prompt = f"""
    ### PERSONA E MISSÃO PRINCIPAL ###
    Você é o "Alfred", o assistente virtual especialista do hotel. Sua missão é ser extremamente prestativo, preciso e amigável.

    ### FONTES DE CONHECIMENTO ###
    1.  **[CATÁLOGO DE QUARTOS]:** Use esta fonte para responder a perguntas sobre tipos de quarto, o que eles incluem, capacidade e preços.
        {knowledge.get('contexto_quartos', 'Nenhuma informação de quartos disponível.')}

    2.  **[INFORMAÇÕES GERAIS DO HOTEL]:** Use esta fonte para responder a perguntas sobre regras, horários e outras informações gerais da estadia.
        {rag_context}
    

    ### HISTÓRICO DA CONVERSA RECENTE ###
    {chat_history}

    ### NOVA PERGUNTA DO USUÁRIO ###
    {user_question}

    ### SUA RESPOSTA:
    """

    print("✅ Prompt final montado. Enviando para o Gemini...")
    # print(prompt) # Descomente esta linha se quiser ver o prompt completo no log

    try:
        # Tenta gerar o conteúdo com a API do Google
        response = generative_model_instance.generate_content(prompt)
        print("✅ Resposta recebida do Gemini.", response)

        # --- DEBUG: Verifique se a resposta tem um texto antes de acessá-lo ---
        if response.parts:
            final_response = response.text
        else:
            # Isso acontece se a API bloquear a resposta por segurança
            print("❌ A resposta do Gemini foi bloqueada ou veio vazia. Verifique o prompt e os filtros de segurança.")
            print(f"Detalhes do bloqueio: {response.prompt_feedback}")
            final_response = "Desculpe, não consegui processar sua pergunta no momento. Poderia reformulá-la?"
            
        return final_response

    except Exception as e:
        # Captura e imprime o erro específico da API do Gemini
        print(f"❌ ERRO CRÍTICO AO CHAMAR A API DO GEMINI: {e}")
        # Retorna uma mensagem de erro genérica para o usuário
        return "Ocorreu um erro ao me comunicar com a inteligência artificial. Por favor, tente novamente."



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
            print("--- DADOS PROCESSADOS ---")
            print(processed_data)
            print("-------------------------")
            return processed_data
    except Exception as e:
        print(f"Erro ao processar evento do Google Calendar: {e}")
        return {
            "response_gemini": "Desculpe, ocorreu um erro ao processar o evento. Tente novamente."
        }
    
    