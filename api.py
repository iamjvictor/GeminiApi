from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from gemini import generate_response_with_gemini
from gemini import process_google_event
from ExtractFromFile import find_relevant_chunks_from_json

app = FastAPI(title="WhatsApp AI Assistant", version="1.0.0")

class WhatsAppMessage(BaseModel):
    user_id: int
    message: str
    chat_history: Optional[str] = ""

@app.post("/process_whatsapp_message")
async def process_whatsapp_message(request: WhatsAppMessage):
    try:
        # Verifica se o Supabase está configurado
        if supabase is None:
            raise HTTPException(
                status_code=500,
                detail="Supabase não configurado. Configure as variáveis SUPABASE_URL e SUPABASE_KEY no arquivo .env"
            )

        # Busca dados do usuário no Supabase usando UUID
        response = (
            supabase.table("users")
            .select("pdf_vector")
            .eq("id", request.user_id)
            .execute()
        )
        
        # Verifica se encontrou dados para o usuário
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Usuário com ID {request.user_id} não encontrado"
            )
        
        # Processa os chunks relevantes
        chunks = find_relevant_chunks_from_json(response.data[0]["pdf_vector"], request.message, 3)
        response_gemini = generate_response_with_gemini(chunks, request.message, request.chat_history)
        
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
