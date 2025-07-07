from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from gemini import generate_response_with_gemini
from ExtractFromFile import find_relevant_chunks_from_json

app = FastAPI(title="WhatsApp AI Assistant", version="1.0.0")

class WhatsAppMessage(BaseModel):
    user_id: int
    message: str

@app.post("/process_whatsapp_message")
async def process_whatsapp_message(request: WhatsAppMessage):

    response = (
        supabase.table("user_data")
        .select("pdf_vector")
        .eq("id", request.user_id)
        .execute()
    )
    chunks = find_relevant_chunks_from_json(response.data[0]["pdf_vector"], request.message, 3)
    response_gemini = generate_response_with_gemini(chunks, request.message)
    try:
        # Retorna os dados recebidos
        return {           
            "response_gemini": response_gemini
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Endpoint para verificar se a API está funcionando."""
    return {"status": "healthy", "service": "WhatsApp AI Assistant"}



