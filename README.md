# WhatsApp AI Assistant API

Esta é uma API FastAPI que integra com WhatsApp, Supabase e Google Gemini para fornecer respostas inteligentes baseadas em documentos PDF.

## 🚀 Como rodar localmente

### 1. Pré-requisitos

- Python 3.8 ou superior
- Conta no Supabase
- Chave da API do Google Gemini

### 2. Configuração do ambiente

#### 2.1. Ativar o ambiente virtual
```bash
# No Windows
.venv\Scripts\activate

# No Linux/Mac
source .venv/bin/activate
```

#### 2.2. Instalar dependências
```bash
pip install -r requirements.txt
```

#### 2.3. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Configurações do Supabase
SUPABASE_URL=sua_url_do_supabase_aqui
SUPABASE_KEY=sua_chave_do_supabase_aqui

# Configuração da API do Google Gemini
GOOGLE_API_KEY=sua_chave_da_api_google_aqui
```

**Como obter as credenciais:**

- **Supabase**: Acesse seu projeto no Supabase e vá em Settings > API
- **Google Gemini**: Acesse [Google AI Studio](https://makersuite.google.com/app/apikey) para obter sua chave da API

### 3. Rodando a API

#### Opção 1: Usando o script personalizado
```bash
python run_api.py
```

#### Opção 2: Usando uvicorn diretamente
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Acessando a API

- **Servidor**: http://localhost:8000
- **Documentação**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## 📋 Endpoints disponíveis

### POST /process_whatsapp_message
Processa mensagens do WhatsApp usando IA.

**Body:**
```json
{
    "user_id": 1,
    "message": "Sua mensagem aqui"
}
```

### GET /health
Verifica se a API está funcionando.

## 🔧 Estrutura do projeto

```
Saas/
├── api.py              # API principal (FastAPI)
├── database.py         # Configuração do Supabase
├── gemini.py           # Integração com Google Gemini
├── ExtractFromFile.py  # Processamento de documentos
├── requirements.txt    # Dependências Python
├── run_api.py         # Script para rodar a API
└── .env               # Variáveis de ambiente (criar)
```

## 🐛 Solução de problemas

### Erro de módulo não encontrado
```bash
pip install -r requirements.txt
```

### Erro de variáveis de ambiente
Verifique se o arquivo `.env` existe e está configurado corretamente.

### Erro de conexão com Supabase
Verifique se as credenciais do Supabase estão corretas no arquivo `.env`.

### Erro de API do Google
Verifique se a chave da API do Google Gemini está correta e ativa.

## 📝 Notas

- A API usa o modelo `gemini-2.0-flash` do Google
- Os documentos são processados e armazenados como vetores no Supabase
- O assistente tem personalidade de surfista e sempre responde com "Aloha!" 