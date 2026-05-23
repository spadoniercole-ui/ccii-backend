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

# --- DATI DI MOCK TEMPORANEI ---
# Questa lista simula i dati del database per sbloccare il frontend
MOCK_TENANTS = [
    {
        "id": "tenant-1",
        "name": "Studio Professionale Rossi",
        "type": "Studio Professionale",
        "max_users": 5,
        "max_companies": 10
    },
    {
        "id": "tenant-2",
        "name": "Azienda Alfa S.r.l.",
        "type": "Azienda",
        "max_users": 2,
        "max_companies": 1
    }
]

# --- ENDPOINT DI SERVIZIO ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- ENDPOINT DI LOGIN ---
@app.post("/login")
def login(req: LoginRequest):
    if req.username == "SuperAdmin":
        if req.password == "CCIIWeb2.0":
            fake_payload = {"role": "SUPER_ADMIN"}
            payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
            fake_token = f"fakeHeader.{payload_b64}.fakeSignature"
            return {"token": fake_token}
        else:
            raise HTTPException(status_code=401, detail="Credenziali errate")
    else:
        raise HTTPException(
            status_code=501, 
            detail="Autenticazione DB non ancora implementata"
        )

# --- ENDPOINT GESTIONE SPAZI (TENANTS) ---
@app.get("/tenants")
def get_tenants():
    # Restituisce la lista di mock per evitare l'errore .map() nel frontend
    return MOCK_TENANTS
