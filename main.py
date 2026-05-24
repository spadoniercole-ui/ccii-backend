from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
import os

from database import engine, Base, get_db
from models import Spazio, User, Role

# Genera le tabelle nel database se non esistono
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cciiplatform.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

class SpazioCreate(BaseModel):
    nome: str
    tipologia: str
    max_utenti: int
    max_aziende: int

@app.get("/")
def home():
    return {"status": "running", "message": "API funzionante correttamente"}

@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # --- 1. LOGICA SUPER ADMIN (Bypass del Database) ---
    if credentials.username == "SuperAdmin" and credentials.password == "CCIIWeb2.0":
        return {
            "status": "success",
            "user_id": 99999,
            "email": "superadmin@system",
            "ruolo": "SUPER_ADMIN",
            "alerts": ["Accesso come Super Admin attivo"]
        }

    # --- 2. LOGICA UTENTI NORMALI ---
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    ora = datetime.now(timezone.utc)
    alert_messaggi = []

    spazio = db.query(Spazio).filter(Spazio.id == user.spazio_id).first() 
    if spazio and spazio.data_scadenza_licenza:
        giorni_licenza = (spazio.data_scadenza_licenza.replace(tzinfo=timezone.utc) - ora).days
        if giorni_licenza <= 0:
            raise HTTPException(status_code=403, detail="Accesso bloccato: Licenza scaduta.")
        elif giorni_licenza < 15:
            alert_messaggi.append(f"Attenzione: La licenza dello spazio scade tra {giorni_licenza} giorni.")

    if user.data_scadenza_password:
        giorni_password = (user.data_scadenza_password.replace(tzinfo=timezone.utc) - ora).days
        if giorni_password <= 0:
            raise HTTPException(status_code=403, detail="Accesso bloccato: Password scaduta.")
        elif giorni_password < 15:
            alert_messaggi.append(f"Attenzione: La tua password scade tra {giorni_password} giorni.")

    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
        "ruolo": user.role.name if user.role else "Nessun ruolo",
        "alerts": alert_messaggi
    }

# --- NUOVE ROTTE PER LA DASHBOARD ---

@app.get("/tenants")
def get_tenants(db: Session = Depends(get_db)):
    """Restituisce la lista di tutti gli spazi (tenants)"""
    spazi = db.query(Spazio).all()
    return [
        {
            "id": s.id,
            "nome": s.nome,
            "data_scadenza": s.data_scadenza_licenza
        } for s in spazi
    ]

@app.post("/tenants")
def create_tenant(dati: SpazioCreate, db: Session = Depends(get_db)):
    """Crea un nuovo spazio"""
    nuovo_spazio = Spazio(
        nome=dati.nome,
        # Assicurati che i campi corrispondano al tuo modello Spazio in models.py
    )
    db.add(nuovo_spazio)
    db.commit()
    db.refresh(nuovo_spazio)
    return {"status": "success", "id": nuovo_spazio.id}

@app.get("/spazi/{spazio_id}")
def leggi_spazio(spazio_id: int, db: Session = Depends(get_db)):
    spazio = db.query(Spazio).filter(Spazio.id == spazio_id).first()
    if spazio is None:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
    return {
        "id": spazio.id,
        "nome": spazio.nome,
        "data_scadenza": spazio.data_scadenza_licenza
    }
