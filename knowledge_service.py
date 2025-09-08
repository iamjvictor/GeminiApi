from cachetools import LRUCache
import requests # Para chamar seu Gateway Node.js

# O cache é criado FORA da classe, como uma instância global no módulo
# maxsize=100: Guarda os dados dos 100 hotéis mais recentemente ativos.
# Quando o 101º chegar, o menos usado recentemente é removido automaticamente.
hotel_cache = LRUCache(maxsize=100) 
from dotenv import load_dotenv
load_dotenv()
import os
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

def get_knowledge_for_hotel(user_id: str):
    """
    Função principal. Busca o conhecimento de um hotel, usando o cache primeiro.
    """
    # Passo 1: Tenta buscar do cache primeiro
    if user_id in hotel_cache:
        print(f"✅ [Cache HIT] Conhecimento encontrado no cache para o hotel {user_id}.")
        return hotel_cache[user_id]

    auth_headers = {
        'x-user-id': user_id,
        'x-api-key': API_SECRET_KEY 
        # Use os nomes exatos que seu middleware 'apiAuthMiddleware' espera
    }

    # Passo 2: Se não está no cache (Cache MISS), busca nos serviços externos
    print(f"⚠️ [Cache MISS] Buscando conhecimento do banco para o hotel {user_id}.")

   

    # Chamada para buscar a lista de quartos no seu Gateway
    rooms_response = requests.post(f"{os.getenv('BACKEND_URL')}/rooms/get-catalog", headers=auth_headers)
    rooms_list = rooms_response.json()

   

    # Formata a lista de quartos para texto (como discutimos)
    formatted_rooms = _format_rooms_for_llm(rooms_list)

    print(f"🛏️ Lista de quartos para o hotel {user_id}: {formatted_rooms}")  # Log da lista de quartos

    knowledge = {       
        "contexto_quartos": formatted_rooms
    }

    # Passo 3: Salva o conhecimento recém-buscado no cache para a próxima vez
    hotel_cache[user_id] = knowledge
    print(f"🧠 Conhecimento armazenado no cache para o hotel {user_id}.", hotel_cache[user_id])

    return knowledge

def invalidate_cache_for_hotel(user_id: str):
    """
    Remove o conhecimento de um hotel específico do cache.
    """
    if user_id in hotel_cache:
        del hotel_cache[user_id]
        print(f"🧹 [Cache CLEARED] Cache invalidado para o hotel {user_id}.")
        return True
    return False

# Dentro do seu arquivo knowledge_service.py

def _format_rooms_for_llm(rooms_json):
    """
    Transforma a lista de quartos em JSON para um texto formatado
    que a IA pode usar como contexto.
    """
    # A resposta vem dentro da chave 'data'
    rooms_list = rooms_json.get('data', [])
    if not rooms_list:
        return "Nenhuma informação de quarto disponível."

    formatted_text = "**Catálogo de Quartos Disponíveis:**\n\n"

    for room in rooms_list:
        formatted_text += f"* Nome do Quarto: {room.get('name', 'N/A')}\n"
        formatted_text += f"  - Descrição: {room.get('description', 'N/A')}\n"
        formatted_text += f"  - Capacidade: Até {room.get('capacity', 'N/A')} pessoas\n"
        formatted_text += f"  - Diária: R$ {room.get('daily_rate', 'N/A')}\n"
        
        # Processa a lista de comodidades
        amenities = room.get('amenities', {})
        available_amenities = [key for key, value in amenities.items() if value is True]
        
        if available_amenities:
            # Formata as comodidades para uma leitura mais amigável
            friendly_amenities = [
                name.replace('tech_', 'Tecnologia: ')
                    .replace('kitchen_', 'Cozinha: ')
                    .replace('comfort_', 'Conforto: ')
                    .replace('outdoor_', 'Área Externa: ')
                    .replace('bathroom_', 'Banheiro: ')
                    .replace('extra_', 'Extra: ')
                    .replace('workspace_', 'Espaço de Trabalho: ')
                for name in available_amenities
            ]
            formatted_text += f"  - Comodidades: {', '.join(friendly_amenities)}\n"
        
        # Adiciona link das fotos se houver
        photos = room.get('photos', [])
        if photos:
            formatted_text += f"  - Fotos: Veja em {', '.join(photos)}\n"

        formatted_text += "\n" # Espaço entre os quartos

    return formatted_text