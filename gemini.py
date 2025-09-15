from dotenv import load_dotenv # Função para carregar variáveis de ambiente de um arquivo .env.
import google.generativeai as genai
 # Biblioteca do Google para interagir com os modelos de IA generativa (Gemini).
import os
import json
import requests
from datetime import datetime
from redis import Redis

load_dotenv() # Carrega as variáveis de ambiente definidas no arquivo .env para o ambiente atual.
api_key = os.getenv('GOOGLE_API_KEY') # Obtém o valor da variável de ambiente 'GOOGLE_API_KEY'.
genai.configure(api_key=api_key)

redis_client = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)



def save_session(whatsapp_number: str, data: dict):
    key = f"session:{whatsapp_number}"
    redis_client.set(key, json.dumps(data), ex=3600)  # expira em 1h

def get_session(whatsapp_number: str):
    key = f"session:{whatsapp_number}"
    session = redis_client.get(key)
    return json.loads(session) if session else None

def update_session(whatsapp_number: str, new_data: dict):
    session = get_session(whatsapp_number) or {}
    session.update(new_data)
    save_session(whatsapp_number, session)
    return session

def clear_session(whatsapp_number: str):
    key = f"session:{whatsapp_number}"
    redis_client.delete(key)

# --- Definição das Ferramentas ---
def verificar_disponibilidade_geral(check_in_date: str, check_out_date: str) -> str:
    """
    Consulta a disponibilidade de quartos de hotel para um período de datas específico.
    Retorna uma lista de quartos disponíveis com seus nomes, preços e IDs.
    """
    # Esta função será chamada pelo Gemini quando necessário
    return f"Verificando disponibilidade para {check_in_date} até {check_out_date}"

def extrair_informacoes_reserva(room_name: str = None, check_in_date: str = None, check_out_date: str = None) -> str:
    """
    Extrai parâmetros de reserva (datas, nome do quarto) da conversa do utilizador.
    """
    return f"Extraindo informações: quarto={room_name}, check-in={check_in_date}, check-out={check_out_date}"

def criar_agendamento_e_gerar_pagamento(room_type_id: int, check_in_date: str, check_out_date: str) -> str:
    """
    Cria uma reserva para um quarto específico após o usuário ter confirmado sua escolha e as datas.
    """
    return f"Criando agendamento para quarto {room_type_id} de {check_in_date} até {check_out_date}"

# Configuração do modelo com ferramentas
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    tools=[
        verificar_disponibilidade_geral,
        extrair_informacoes_reserva,
        criar_agendamento_e_gerar_pagamento
    ]
)

print("Ferramentas e configuração criadas com sucesso!")


def chamar_api_disponibilidade(hotel_id: str, check_in_date: str, check_out_date: str, lead_whatsapp_number: str):
    backend_url = os.getenv("BACKEND_URL")
    api_url = f"{backend_url}/bookings/{hotel_id}/availability-report"
    backend_api_secret = os.getenv("API_SECRET_KEY")
    headers = {"x-api-key": backend_api_secret}
    params = {"checkIn": check_in_date, "checkOut": check_out_date, "leadWhatsappNumber": lead_whatsapp_number  }
    print(f"🔍 [DEBUG DISPONIBILIDADE] Parâmetros: {params}")
    try:
        response = requests.get(api_url, json=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao chamar API de disponibilidade: {e}")
        return {"error": "Falha ao verificar disponibilidade no sistema."}

def chamar_api_agendamento(hotel_id: str, lead_whatsapp_number: str, room_type_id: int, check_in_date: str, check_out_date: str, total_price: float):
    backend_url = os.getenv("BACKEND_URL")
    api_url = f"{backend_url}/bookings/create"
    backend_api_secret = os.getenv("API_SECRET_KEY")
    headers = {"x-api-key": backend_api_secret}
    body = {
        "user_id": hotel_id,
        "lead_whatsapp_number": lead_whatsapp_number,
        "room_type_id": room_type_id,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "total_price": total_price
    }

    try:
        response = requests.post(api_url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao chamar API de agendamento: {e}")
        return {"error": "Falha ao criar agendamento no sistema."}

def get_room_id_from_name(availability_report: list, room_name_mentioned: str) -> int | None:
    if not availability_report or not room_name_mentioned: 
        return None
    
    search_name = room_name_mentioned.lower().strip()
    print(f"🔍 [BUSCA QUARTO] Procurando por: '{search_name}'")
    
    for room in availability_report:
        room_name = room.get("name", "").lower()
        room_id = room.get("id")
        is_available = room.get("isAvailable", False)
        
        print(f"🔍 [BUSCA QUARTO] Verificando: '{room_name}' (ID: {room_id}, Disponível: {is_available})")
        
        if search_name in room_name:
            if is_available:
                print(f"✅ [BUSCA QUARTO] Encontrado e disponível: {room_name} (ID: {room_id})")
                return room_id
            else:
                print(f"⚠️ [BUSCA QUARTO] Encontrado mas indisponível: {room_name} (ID: {room_id})")
                # Retorna o ID mesmo se não estiver disponível, para mostrar erro específico
                return room_id
    
    print(f"❌ [BUSCA QUARTO] Quarto não encontrado: '{search_name}'")
    return None

def calculate_total_price(check_in_date: str, check_out_date: str, room_id: int, availability_report: list) -> float | None:
    try:
        start_date = datetime.strptime(check_in_date, "%Y-%m-%d")
        end_date = datetime.strptime(check_out_date, "%Y-%m-%d")
        num_nights = (end_date - start_date).days

        if num_nights <= 0:
            print(f"❌ [CÁLCULO PREÇO] Número de noites inválido: {num_nights}")
            return None

        daily_rate = None
        room_found = False
        for room in availability_report:
            if room.get("id") == room_id:
                daily_rate = room.get("dailyRate")
                is_available = room.get("isAvailable", False)
                room_found = True
                print(f"🔍 [CÁLCULO PREÇO] Quarto encontrado: ID {room_id}, Diária: R$ {daily_rate}, Disponível: {is_available}")
                break
        
        if not room_found:
            print(f"❌ [CÁLCULO PREÇO] Quarto ID {room_id} não encontrado no relatório")
            return None
            
        if daily_rate is None:
            print(f"❌ [CÁLCULO PREÇO] Diária não encontrada para quarto ID {room_id}")
            return None

        total_price = daily_rate * num_nights
        print(f"💰 [CÁLCULO PREÇO] Total: R$ {daily_rate} × {num_nights} noites = R$ {total_price:.2f}")
        return total_price
        
    except (ValueError, TypeError) as e:
        print(f"❌ [CÁLCULO PREÇO] Erro ao calcular preço: {e}")
        return None

# ============================ 
# FUNÇÃO PRINCIPAL (Gemini + Redis)
# ============================ 
def generate_response_with_gemini(rag_context: str, user_question: str, chat_history: list, knowledge: dict, hotel_id: str, lead_whatsapp_number: str):
    print(f"\n--- NOVA REQUISIÇÃO PARA {lead_whatsapp_number} ---")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Obter dados da sessão
        session_data = get_session(lead_whatsapp_number) or {}
        print(f"📋 [SESSÃO INICIAL] Dados para {lead_whatsapp_number}: {json.dumps(session_data, indent=2)}")

        # Construir contexto da conversa
        chat_context = ""
        if chat_history:
            for msg in chat_history[-5:]:  # Últimas 5 mensagens
                role = msg.get("role", "user")
                content = msg.get("content", "")
                chat_context += f"{role}: {content}\n"
        print(chat_context)
        print (knowledge)
        # Instruções do sistema
        system_prompt = f"""
            Você é Alfred, um assistente de reservas de hotel especializado em WhatsApp.

            **CONTEXTO ATUAL:**
            - Data de hoje: {current_date}
            - Hotel ID: {hotel_id}
            - Quartos disponíveis: {json.dumps(knowledge, ensure_ascii=False)}
            - Regras e informações do hotel: {rag_context}

            **DADOS JÁ COLETADOS:**
            {json.dumps(session_data, indent=2, ensure_ascii=False)}

            **HISTÓRICO DA CONVERSA:**
            {chat_context}

            **SUAS FUNÇÕES:**
            1. **extrair_informacoes_reserva**: Use APENAS quando o usuário mencionar datas específicas (ex: "15 de dezembro", "20/12") ou nomes de quartos (ex: "Suíte Master", "Quarto Simples")
            2. **verificar_disponibilidade_geral**: Use APENAS quando tiver datas de check-in e check-out para verificar disponibilidade
            3. **criar_agendamento_e_gerar_pagamento**: Use APENAS quando tiver todos os dados (datas + quarto + disponibilidade confirmada)

            **REGRAS IMPORTANTES:**
            - Se o usuário perguntar sobre quartos disponíveis SEM mencionar datas específicas, responda diretamente com informações dos quartos
            - Se o usuário mencionar datas específicas, chame extrair_informacoes_reserva
            - Se o usuário mencionar um quarto específico para reservar, chame criar_agendamento_e_gerar_pagamento
            - Seja amigável e direto
            - Use os dados da sessão para tomar decisões inteligentes

            **EXEMPLOS:**
            - "Quais quartos vocês têm?" → Responda diretamente com lista de quartos
            - "Quero reservar de 15 a 20 de dezembro" → Chame extrair_informacoes_reserva
            - "Gostei da Suíte Master" → Chame criar_agendamento_e_gerar_pagamento (se tiver datas na sessão)
            """

        # Preparar mensagem para o modelo
        full_prompt = f"{system_prompt}\n\nUsuário: {user_question}"        
        print(f"💬 [PERGUNTA DO USUÁRIO]: {user_question}")

        # Gerar resposta com o modelo
        response = model.generate_content(full_prompt)
        
        # Verificar se há chamadas de função primeiro
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    print(f"🛠️ [CHAMADA DE FERRAMENTA]: {function_call.name}")
                    print(f"   - Argumentos: {function_call.args}")
                    
                    # Processar chamada de função
                    result = process_function_call(
                        function_call, 
                        hotel_id, 
                        lead_whatsapp_number, 
                        session_data,
                        user_question
                    )
                    
                    if result:
                        return result
                elif hasattr(part, 'text') and part.text:
                    print(f"🤖 [RESPOSTA DA IA]: {part.text}")
                    return part.text

        # Se não há partes ou não conseguiu processar
        try:
            if response.text:
                print(f"🤖 [RESPOSTA DA IA]: {response.text}")
                return response.text
        except ValueError:
            # Se não conseguiu converter para text (provavelmente function_call)
            pass

        return "Desculpe, não consegui processar sua mensagem. Tente novamente."

    except Exception as e:
        print(f"❌ [ERRO CRÍTICO] em generate_response_with_gemini: {e}")
        import traceback
        traceback.print_exc()
        return "Ocorreu um erro inesperado ao processar sua solicitação. Por favor, tente novamente."


def process_function_call(function_call, hotel_id: str, lead_whatsapp_number: str, session_data: dict, user_question: str = ""):
    """
    Processa chamadas de função do Gemini e executa a lógica de negócio
    """
    function_name = function_call.name
    args = dict(function_call.args)
    
    print(f"🔄 [PROCESSANDO FUNÇÃO] {function_name} com args: {args}")
    
    try:
        if function_name == "extrair_informacoes_reserva":
            # Verificar se as datas mudaram antes de atualizar
            current_session = get_session(lead_whatsapp_number) or {}
            old_check_in = current_session.get("check_in_date")
            old_check_out = current_session.get("check_out_date")
            new_check_in = args.get("check_in_date")
            new_check_out = args.get("check_out_date")
            
            # Se as datas mudaram, limpar a disponibilidade anterior
            if (old_check_in != new_check_in or old_check_out != new_check_out) and current_session.get("availability"):
                print("🔄 [DADOS MUDARAM] Limpando disponibilidade anterior...")
                current_session.pop("availability", None)
                save_session(lead_whatsapp_number, current_session)
            
            # Atualizar sessão com informações extraídas
            update_session(lead_whatsapp_number, args)
            print(f"💾 [SESSÃO ATUALIZADA] com extração: {json.dumps(get_session(lead_whatsapp_number), indent=2)}")
            
            # Verificar se temos dados suficientes para próxima ação
            session_data = get_session(lead_whatsapp_number)
            check_in = session_data.get("check_in_date")
            check_out = session_data.get("check_out_date")
            print(f"🔍 [DEBUG SESSÃO] sessão completa: {session_data}")
         
            
            # Verificar se precisa consultar disponibilidade
            current_availability = session_data.get("availability")
            needs_availability_check = (
                check_in and check_out and (
                    not current_availability or  # Não tem dados de disponibilidade
                    "error" in current_availability or  # Tem erro na consulta anterior
                    (isinstance(current_availability, dict) and (
                        current_availability.get("checkIn") != check_in or  # Datas mudaram
                        current_availability.get("checkOut") != check_out
                    ))
                )
            )
            
            if needs_availability_check:
                # Temos datas, vamos verificar disponibilidade
                print("➡️ [AUTO-AÇÃO] Verificando disponibilidade...")
                print(f"🔍 [DEBUG DISPONIBILIDADE] Hotel ID: {hotel_id}")
                print(f"🔍 [DEBUG DISPONIBILIDADE] Check-in: {check_in}")
                print(f"🔍 [DEBUG DISPONIBILIDADE] Check-out: {check_out}")
                print(f"🔍 [DEBUG DISPONIBILIDADE] Lead WhatsApp Number: {lead_whatsapp_number}")
                availability_result = chamar_api_disponibilidade(hotel_id, check_in, check_out, lead_whatsapp_number)
                
                # Se a resposta é uma lista (formato correto), adicionar metadados
                if isinstance(availability_result, list):
                    # Criar um objeto com a lista e metadados
                    availability_data = {
                        "rooms": availability_result,
                        "checkIn": check_in,
                        "checkOut": check_out
                    }
                    update_session(lead_whatsapp_number, {"availability": availability_data})
                else:
                    # Se é um erro, manter como está
                    update_session(lead_whatsapp_number, {"availability": availability_result})
                
                # Gerar resposta humanizada usando o Gemini
                return generate_humanized_response(
                    user_question, 
                    session_data, 
                    availability_result, 
                    "availability_check"
                )
            
            # Se não precisa verificar disponibilidade, gerar resposta baseada no que foi extraído
            return generate_humanized_response(
                user_question, 
                session_data, 
                None, 
                "information_extraction"
            )

        elif function_name == "verificar_disponibilidade_geral":
            check_in = args.get("check_in_date")
            check_out = args.get("check_out_date")
            
            if not check_in or not check_out:
                return "❌ Preciso das datas de check-in e check-out para verificar disponibilidade."
            
            # Verificar se as datas mudaram antes de atualizar
            current_session = get_session(lead_whatsapp_number) or {}
            old_check_in = current_session.get("check_in_date")
            old_check_out = current_session.get("check_out_date")
            
            # Se as datas mudaram, limpar a disponibilidade anterior
            if (old_check_in != check_in or old_check_out != check_out) and current_session.get("availability"):
                print("🔄 [DADOS MUDARAM] Limpando disponibilidade anterior...")
                current_session.pop("availability", None)
                save_session(lead_whatsapp_number, current_session)
            
            # Atualizar sessão com datas
            update_session(lead_whatsapp_number, {"check_in_date": check_in, "check_out_date": check_out})
            
            # Verificar disponibilidade
            availability_result = chamar_api_disponibilidade(hotel_id, check_in, check_out, lead_whatsapp_number)
            
            # Se a resposta é uma lista (formato correto), adicionar metadados
            if isinstance(availability_result, list):
                # Criar um objeto com a lista e metadados
                availability_data = {
                    "rooms": availability_result,
                    "checkIn": check_in,
                    "checkOut": check_out
                }
                update_session(lead_whatsapp_number, {"availability": availability_data})
            else:
                # Se é um erro, manter como está
                update_session(lead_whatsapp_number, {"availability": availability_result})
            
            # Obter dados atualizados da sessão
            session_data = get_session(lead_whatsapp_number)
            
            # Gerar resposta humanizada usando o Gemini
            return generate_humanized_response(
                user_question, 
                session_data, 
                availability_result, 
                "availability_check"
            )

        elif function_name == "criar_agendamento_e_gerar_pagamento":
            room_id = args.get("room_type_id")
            check_in = args.get("check_in_date")
            check_out = args.get("check_out_date")
            
            if not all([room_id, check_in, check_out]):
                return "❌ Preciso do ID do quarto e das datas para criar o agendamento."
            
            # Obter dados da sessão para calcular preço
            session_data = get_session(lead_whatsapp_number)
            availability_data = session_data.get("availability", {})
            
            if not availability_data:
                return "❌ Preciso verificar a disponibilidade primeiro."
            
            # Extrair lista de quartos do formato correto
            if isinstance(availability_data, dict) and "rooms" in availability_data:
                availability_report = availability_data["rooms"]
            elif isinstance(availability_data, list):
                availability_report = availability_data
            else:
                return "❌ Dados de disponibilidade inválidos."
            
            # Verificar se o quarto está disponível
            room_available = False
            room_name = "Quarto"
            for room in availability_report:
                if room.get("id") == room_id:
                    room_available = room.get("isAvailable", False)
                    room_name = room.get("name", "Quarto")
                    break
            
            if not room_available:
                return f"❌ O quarto '{room_name}' não está mais disponível para essas datas. Por favor, escolha outro quarto ou datas diferentes."
            
            # Calcular preço total
            total_price = calculate_total_price(check_in, check_out, room_id, availability_report)
            if not total_price:
                return "❌ Não foi possível calcular o preço total. Verifique as datas e o quarto."
            
            # Criar agendamento
            booking_result = chamar_api_agendamento(hotel_id, lead_whatsapp_number, room_id, check_in, check_out, total_price)
            
            if "error" not in booking_result:
                # Limpar sessão após sucesso
                clear_session(lead_whatsapp_number)
                return f"🎉 Reserva criada com sucesso!\n\n🏨 Quarto: {room_name}\n💰 Preço total: R$ {total_price:.2f}\n📅 Check-in: {check_in}\n📅 Check-out: {check_out}\n\n🔗 Link para pagamento: {booking_result.get('paymentUrl', 'Link não disponível')}"
            else:
                return f"❌ Erro ao criar reserva: {booking_result.get('error', 'Erro desconhecido')}"

    except Exception as e:
        print(f"❌ [ERRO] ao processar função {function_name}: {e}")
        return f"❌ Erro ao processar {function_name}: {str(e)}"
    
    return None


def generate_humanized_response(user_question: str, session_data: dict, availability_result: any, action_type: str) -> str:
    """
    Gera uma resposta humanizada usando o Gemini baseada no contexto e resultados
    """
    try:
        # Construir contexto para o Gemini
        context = f"""
        Você é Alfred, um assistente de reservas de hotel especializado em WhatsApp.

        **AÇÃO REALIZADA:** {action_type}
        **PERGUNTA DO USUÁRIO:** {user_question}

        **DADOS DA SESSÃO:**
        {json.dumps(session_data, indent=2, ensure_ascii=False)}

        **RESULTADO DA AÇÃO:**
        {json.dumps(availability_result, indent=2, ensure_ascii=False) if availability_result else "Nenhum resultado específico"}

        **INSTRUÇÕES:**
        - Seja natural e conversacional
        - Se faltam informações (como data de checkout), pergunte de forma amigável
        - Se há quartos disponíveis, apresente-os de forma atrativa
        - Se há erros, explique de forma clara e ofereça alternativas
        - Use emojis quando apropriado
        - Seja direto mas acolhedor

        **EXEMPLOS DE RESPOSTAS:**
        - Se faltam datas: "Perfeito! Você mencionou a suíte master. Para verificar a disponibilidade, preciso saber as datas. Qual seria a data de check-in e check-out?"
        - Se há quartos disponíveis: "Ótimo! Encontrei algumas opções para você: [listar quartos]. Qual desses quartos te interessa?"
        - Se há erro: "Desculpe, tive um problema técnico. Vou tentar novamente. Pode me informar as datas novamente?"
        """

        # Gerar resposta com o modelo
        response = model.generate_content(context)
        
        if response.text:
            return response.text
        else:
            # Fallback para resposta padrão
            return "✅ Informações processadas! Como posso ajudar mais?"
            
    except Exception as e:
        print(f"❌ [ERRO] ao gerar resposta humanizada: {e}")
        # Fallback para resposta padrão baseada no tipo de ação
        if action_type == "availability_check":
            if availability_result and "error" not in availability_result:
                return f"✅ Verifiquei a disponibilidade! {format_availability_response(availability_result)}"
            else:
                return "❌ Tive um problema ao verificar a disponibilidade. Pode tentar novamente?"
        else:
            return "✅ Informações registradas! Como posso ajudar mais?"


def format_availability_response(availability_data):
    """
    Formata a resposta de disponibilidade de forma amigável
    """
    if not availability_data or "error" in availability_data:
        return "❌ Nenhum quarto disponível para essas datas."
    
    if isinstance(availability_data, list):
        response = "🏨 Quartos disponíveis:\n\n"
        available_rooms = []
        unavailable_rooms = []
        
        for room in availability_data:
            name = room.get("name", "Quarto")
            price = room.get("dailyRate", 0)
            room_id = room.get("id", 0)
            is_available = room.get("isAvailable", False)
            available_count = room.get("availableCount", 0)
            description = room.get("description", "")
            
            room_info = f"• {name} - R$ {price:.2f}/noite"
            if description:
                room_info += f" ({description})"
            room_info += f" (ID: {room_id})"
            
            if is_available and available_count > 0:
                available_rooms.append(room_info)
            else:
                unavailable_rooms.append(room_info)
        
        if available_rooms:
            response += "✅ **DISPONÍVEIS:**\n"
            for room in available_rooms:
                response += f"{room}\n"
            response += "\n"
        
        if unavailable_rooms:
            response += "❌ **INDISPONÍVEIS:**\n"
            for room in unavailable_rooms:
                response += f"{room}\n"
        
        if not available_rooms and not unavailable_rooms:
            response += "❌ Nenhum quarto encontrado."
            
        return response
    
    return "❌ Dados de disponibilidade inválidos."


def process_google_event(payload: dict) -> dict:
    """
    Processa o evento recebido do Google Calendar e gera uma resposta usando o modelo Gemini.
    
    Args:
        payload (dict): Payload do evento do Google Calendar
    
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

        response = model.generate_content(prompt)
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


def test_booking_flow():
    """
    Função de teste para demonstrar o fluxo completo de agendamento
    """
    print("🧪 INICIANDO TESTE DO FLUXO DE AGENDAMENTO")
    print("=" * 50)
    
    # Dados de teste
    hotel_id = "test_hotel_123"
    lead_whatsapp = "5521999999999"
    rag_context = "Hotel de luxo com quartos confortáveis"
    knowledge = {
        "rooms": [
            {"id": 1, "name": "Suíte Master", "dailyRate": 200.0},
            {"id": 2, "name": "Quarto Simples", "dailyRate": 100.0},
            {"id": 3, "name": "Quarto Duplo", "dailyRate": 150.0}
        ]
    }
    
    # Simular conversa
    test_messages = [
        "Olá, gostaria de fazer uma reserva",
        "Quero reservar de 15 a 20 de dezembro",
        "Gostei da Suíte Master, pode reservar?"
    ]
    
    chat_history = []
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📱 MENSAGEM {i}: {message}")
        print("-" * 30)
        
        response = generate_response_with_gemini(
            rag_context=rag_context,
            user_question=message,
            chat_history=chat_history,
            knowledge=knowledge,
            hotel_id=hotel_id,
            lead_whatsapp_number=lead_whatsapp
        )
        
        print(f"🤖 RESPOSTA: {response}")
        
        # Adicionar à conversa
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": response})
        
        print(f"💾 SESSÃO ATUAL: {json.dumps(get_session(lead_whatsapp), indent=2)}")
    
    print("\n✅ TESTE CONCLUÍDO!")
    print("=" * 50)


if __name__ == "__main__":
    # Executar teste se o arquivo for executado diretamente
    test_booking_flow()