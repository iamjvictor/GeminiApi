from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from database import supabase
from gemini import generate_response_with_gemini
from gemini import process_google_event
from ExtractFromFile import process_rag_pipeline
from knowledge_service import invalidate_cache_for_hotel, get_knowledge_for_hotel
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from generateChunks import generate_vectorized_chunks


app = FastAPI(title="WhatsApp AI Assistant", version="1.0.0")

API_SECRET_KEY = os.getenv("API_SECRET_KEY")

async def verify_api_key(request: Request):
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou ausente."
        )

class WhatsAppMessage(BaseModel):
    user_id: str
    message: str
    chat_history: Optional[str] = ""
    lead_whatsapp_number: Optional[str] = ""

class DocumentToIndex(BaseModel):
    full_text: str

def parse_chat_history(history_string: str) -> List[Dict[str, any]]:
    if not history_string:
        return []

    parsed_history = []
    lines = history_string.strip().split('\n')
    
    for line in lines:
        if line.startswith("Usuário: "):
            role = "user"
            text = line.replace("Usuário: ", "").strip()
        elif line.startswith("Alfred: "):
            role = "model"
            text = line.replace("Alfred: ", "").strip()
        else:
            continue # Ignora linhas mal formatadas

        parsed_history.append({"role": role, "parts": [{"text": text}]})
    
    return parsed_history

@app.post("/process_whatsapp_message", dependencies=[Depends(verify_api_key)])
async def process_whatsapp_message(request: WhatsAppMessage):
    
    try:
        knowledge = get_knowledge_for_hotel(str(request.user_id))
        rag_context = process_rag_pipeline(request.user_id, request.message) 
        
        # Converte o histórico de string para o formato de lista do Gemini
        parsed_chat_history = parse_chat_history(request.chat_history)
        print(f"🔍 [DEBUG] request.lead_whatsapp_number: {request.lead_whatsapp_number}")
        response_gemini = generate_response_with_gemini(
            rag_context=rag_context,
            user_question=request.message, 
            chat_history=parsed_chat_history, # Passa o histórico parseado
            knowledge=knowledge, 
            hotel_id=request.user_id, 
            lead_whatsapp_number=request.lead_whatsapp_number
        )

        return {
            "response_gemini": response_gemini
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Endpoint para verificar se a API está funcionando."""
    return {
        "status": "healthy", 
        "service": "WhatsApp AI Assistant",
        "supabase_configured": supabase is not None
    }

@app.post("/index-document")
async def index_document(document: DocumentToIndex):
    """
    Endpoint que recebe o texto completo de um documento e retorna os chunks vetorizados.
    """
    try:
        print("🏭 [Fábrica] Recebido novo documento para indexação via API...")
        # Chama a função principal do nosso novo arquivo
        vectorized_chunks = generate_vectorized_chunks(document.full_text)
        return vectorized_chunks
    except (ValueError, RuntimeError) as e:
        # Erros esperados (ex: texto vazio)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erros inesperados
        print(f"❌ ERRO na fábrica de embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno no serviço de IA: {str(e)}")


@app.post("/handleWebhook")
def handle_webhook(promptPayload: dict):
    """
    Endpoint para lidar com eventos do Google Calendar.
    """
    try:
        # Chama a função que processa o evento
        response = process_google_event(promptPayload)
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar webhook: {str(e)}"
        )




@app.post("/invalidate-cache/{user_id}")
def invalidate_cache(user_id):
    # Você pode adicionar uma chave de segurança aqui para garantir que
    # apenas seu Gateway pode chamar este endpoint.
    success = invalidate_cache_for_hotel(user_id)
    if success:
        return {"message": f"Cache para o usuário {user_id} foi limpo."}, 200
    else:
        return {"message": f"Nenhum cache encontrado para o usuário {user_id}."}, 404
