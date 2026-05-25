from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List
from dependencies import require_superadmin

# Importazione dei moduli
from database import engine, Base, get_db
import models
from utils import get_password_hash, verify_password

# 1. Inizializza l'app
app = FastAPI()

# 2. Configura il middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# --- SCHEMI DATI (Per l'inserimento) ---

class LoginRequest(BaseModel):
    username: str
    password: str

class SpazioCreate(BaseModel):
    nome: str
    data_scadenza_licenza: str # YYYY-MM-DD

class UserCreate(BaseModel):
    email: str
    password: str
    spazio_id: int
    role_id: int

class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str 

# --- ROTTE ---

@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # ... (mantieni la tua logica di bypass e login standard)
    pass

# --- ROTTE SUPER ADMIN (Inserimento Dati) ---

@app.post("/superadmin/spazi", status_code=status.HTTP_201_CREATED)
def create_spazio(
    dati: SpazioCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin) # <-- Protezione attivata
):
    data_scadenza = datetime.strptime(dati.data_scadenza_licenza, "%Y-%m-%d")
    nuovo_spazio = models.Spazio(nome=dati.nome, data_scadenza_licenza=data_scadenza)
    db.add(nuovo_spazio)
    db.commit()
    return {"status": "success", "id": nuovo_spazio.id}

@app.post("/superadmin/utenti", status_code=status.HTTP_201_CREATED)
def create_user(
    dati: UserCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin) # <-- Protezione attivata
):
    if db.query(models.User).filter(models.User.email == dati.email).first():
        raise HTTPException(status_code=400, detail="Email già registrata")
    
    hashed = get_password_hash(dati.password)
    nuovo_utente = models.User(email=dati.email, password=hashed, spazio_id=dati.spazio_id, role_id=dati.role_id)
    db.add(nuovo_utente)
    db.commit()
    return {"status": "success", "user_id": nuovo_utente.id}

@app.post("/superadmin/licenze", status_code=status.HTTP_201_CREATED)
def create_licenza(
    dati: LicenzaCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin) # <-- Protezione attivata
):
    nuova_licenza = models.Licenza(
        intestatario=dati.intestatario,
        max_spazi=dati.max_spazi,
        max_utenti_totali=dati.max_utenti_totali,
        max_aziende_totali=dati.max_aziende_totali,
        data_scadenza=datetime.strptime(dati.data_scadenza, "%Y-%m-%d").date()
    )
    db.add(nuova_licenza)
    db.commit()
    return {"status": "success", "id": nuova_licenza.id}

@app.get("/superadmin/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db), 
    admin: models.User = Depends(require_superadmin) # <-- Protezione attivata
):
    return {
        "status": "success",
        "data": {
            "total_spazi": db.query(models.Spazio).count(),
            # ... resto del codice
        }
    }id": nuova_licenza.id}
