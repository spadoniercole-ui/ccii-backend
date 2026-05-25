import sys
import os
print("Current Working Directory:", os.getcwd())
print("Python Path:", sys.path)
# Elenca i file nella cartella corrente per vedere se 'routes' esiste
print("Files in current directory:", os.listdir('.'))

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Errore interno del sistema. Contattare l'amministratore."},
    )

from fastapi import FastAPI
from app.routes.admin_setup import router as admin_setup_router

app = FastAPI()

# Include il router
app.include_router(admin_setup_router)

@app.get("/")
def root():
    return {"status": "ok"}

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List
from contextlib import asynccontextmanager

# Importazione moduli locali
from database import engine, Base, get_db, SessionLocal
import models
from utils import get_password_hash
from dependencies import require_superadmin

# --- LIFESPAN: Gestione inizializzazione ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Creazione tabelle
    Base.metadata.create_all(bind=engine)
    
    # 2. Inserimento Super Admin se non esiste
    db = SessionLocal()
    admin_exists = db.query(models.User).filter(models.User.is_superuser == True).first()
    
    if not admin_exists:
        print("--- Inizializzazione: Creazione Super Admin di default ---")
        hashed_pw = get_password_hash("PasswordSicura123!")
        # Assicurati che i campi obbligatori del tuo modello siano qui
        # Se spazio_id o role_id sono necessari, impostali a valori dummy iniziali
        nuovo_admin = models.User(
            email="admin@tuosito.com",
            password=hashed_pw,
            is_superuser=True,
            # Se nel DB questi campi sono necessari, inserisci valori di default
            # spazio_id=1, role_id=1 
        )
        db.add(nuovo_admin)
        db.commit()
    
    db.close()
    yield
    # Codice di shutdown (opzionale)

# 1. Inizializza l'app con il lifespan
app = FastAPI(lifespan=lifespan)

# 2. Configura il middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMI DATI ---

class LoginRequest(BaseModel):
    username: str
    password: str

class SpazioCreate(BaseModel):
    nome: str
    data_scadenza_licenza: str

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
    # Logica di login
    return {"message": "Implementare logica di autenticazione"}

# --- ROTTE SUPER ADMIN ---

@app.post("/superadmin/spazi", status_code=status.HTTP_201_CREATED)
def create_spazio(
    dati: SpazioCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin)
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
    admin: models.User = Depends(require_superadmin)
):
    if db.query(models.User).filter(models.User.email == dati.email).first():
        raise HTTPException(status_code=400, detail="Email già registrata")
    
    hashed = get_password_hash(dati.password)
    nuovo_utente = models.User(
        email=dati.email, 
        password=hashed, 
        spazio_id=dati.spazio_id, 
        role_id=dati.role_id
    )
    db.add(nuovo_utente)
    db.commit()
    return {"status": "success", "user_id": nuovo_utente.id}

@app.post("/superadmin/licenze", status_code=status.HTTP_201_CREATED)
def create_licenza(
    dati: LicenzaCreate, 
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin)
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
    admin: models.User = Depends(require_superadmin) 
):
    return {
        "status": "success",
        "data": {
            "total_spazi": db.query(models.Spazio).count(),
        }
    }
