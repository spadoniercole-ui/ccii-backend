from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import json

app = FastAPI()

# --- MIDDLEWARE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMI DATI ---
class LoginRequest(BaseModel):
    username: str
    password: str

# --- ENDPOINT DI SERVIZIO ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- ENDPOINT DI LOGIN ---
@app.post("/login")
def login(req: LoginRequest):
    # 1. Gestione Super Admin (Accesso hardcoded)
    if req.username == "SuperAdmin":
        if req.password == "CCIIWeb2.0":
            # Generazione di un finto token JWT leggibile dal frontend (decodifica Base64)
            fake_payload = {"role": "SUPER_ADMIN"}
            # Codifichiamo in base64url rimuovendo il padding "=" per rispettare lo standard JWT
            payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
            
            # Un token JWT ha sempre 3 parti: Header.Payload.Signature
            fake_token = f"fakeHeader.{payload_b64}.fakeSignature"
            
            return {"token": fake_token}
        else:
            # Se la password è sbagliata (anche per uno spazio in più), blocco immediato
            raise HTTPException(status_code=401, detail="Credenziali errate")

    # 2. Gestione Utenti (Da implementare a Database)
    else:
        # Quando collegherai PostgreSQL, sostituirai questo blocco con la ricerca
        # dell'utente (Admin di spazio o standard), la verifica della password hashata
        # e la logica di blocco al 5° tentativo fallito.
        raise HTTPException(
            status_code=501, 
            detail="Autenticazione DB non ancora implementata per le utenze standard"
        )
