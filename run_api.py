import uvicorn
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

if __name__ == "__main__":
    # Configurações do servidor
    host = "0.0.0.0"  # Permite acesso externo
    port = 8000        # Porta padrão do FastAPI
    
    print("🚀 Iniciando WhatsApp AI Assistant API...")
    print(f"📡 Servidor rodando em: http://{host}:{port}")
    print("📚 Documentação da API: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/health")
    print("\nPressione Ctrl+C para parar o servidor")
    
    # Inicia o servidor
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=True,  # Recarrega automaticamente quando há mudanças
        log_level="info"
    ) 