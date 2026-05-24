from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List

# Import dei modelli e database
from database import engine, Base, get_db
from models import Spazio, User, Role, Licenza 

# 1. Inizializza l'app PRIMA di usarla
app = FastAPI()

# 2. Configura il middleware DOPO aver creato l'app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Genera le tabelle nel database
Base.metadata.create_all(bind=engine)

# --- SCHEMI DATI ---

class LoginRequest(BaseModel):
    username: str
    password: str

class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str # Formato YYYY-MM-DD

# --- ROTTE ---

@app.get("/")
def home():
    return {"status": "running", "message": "API funzionante correttamente"}

@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # 1. Bypass Super Admin
    if credentials.username == "SuperAdmin" and credentials.password == "CCIIWeb2.0":
        return {
            "status": "success",
            "user_id": 99999,
            "email": "superadmin@system",
            "ruolo": "SUPER_ADMIN",
            "alerts": ["Accesso come Super Admin attivo"]
        }

    # 2. Login Standard
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # Logica scadenze
    ora = datetime.now(timezone.utc)
    alert_messaggi = []

    spazio = db.query(Spazio).filter(Spazio.id == user.spazio_id).first() 
    if spazio and spazio.data_scadenza_licenza:
        giorni_licenza = (spazio.data_scadenza_licenza.replace(tzinfo=timezone.utc) - ora).days
        if giorni_licenza <= 0:
            raise HTTPException(status_code=403, detail="Accesso bloccato: Licenza scaduta.")
        elif giorni_licenza < 15:
            alert_messaggi.append(f"Attenzione: La licenza dello spazio scade tra {giorni_licenza} giorni.")

    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
        "ruolo": user.role.name if user.role else "Nessun ruolo",
        "alerts": alert_messaggi
    }

# --- ROTTE TENANTS ---

@app.get("/tenants")
def get_tenants(db: Session = Depends(get_db)):
    spazi = db.query(Spazio).all()
    return [{"id": s.id, "nome": s.nome} for s in spazi]

# --- ROTTE SUPER ADMIN (Gestione Licenze) ---

@app.get("/superadmin/licenze")
def get_licenze(db: Session = Depends(get_db)):
    licenze = db.query(Licenza).all()
    return [
        {
            "id": l.id,
            "intestatario": l.intestatario,
            "max_spazi": l.max_spazi,
            "max_utenti_totali": l.max_utenti_totali,
            "max_aziende_totali": l.max_aziende_totali,
            "data_scadenza": str(l.data_scadenza) # Convertito in stringa per sicurezza JSON
        } for l in licenze
    ]

@app.post("/superadmin/licenze")
def create_licenza(dati: LicenzaCreate, db: Session = Depends(get_db)):
    nuova_licenza = Licenza(
        intestatario=dati.intestatario,
        max_spazi=dati.max_spazi,
        max_utenti_totali=dati.max_utenti_totali,
        max_aziende_totali=dati.max_aziende_totali,
        data_scadenza=datetime.strptime(dati.data_scadenza, "%Y-%m-%d").date()
    )
    db.add(nuova_licenza)
    db.commit()
    db.refresh(nuova_licenza)
    return {"status": "success", "id": nuova_licenza.id}
