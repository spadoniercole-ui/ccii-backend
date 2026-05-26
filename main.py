import os
import sys
import bcrypt
from datetime import datetime, timedelta, date
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import jwt

# Importazioni piatte (tutti questi file sono nella stessa cartella di main.py)
from database import engine, Base, get_db, SessionLocal
from utils import get_password_hash, verify_password
import models

# --- CONFIGURAZIONE JWT ---
SECRET_KEY = "CAMBIA_QUESTA_CHIAVE_SEGRETISSIMA_IN_PRODUZIONE"
ALGORITHM = "HS256"

# --- LOGICA EX-AUTH.PY (INTEGRATA) ---
def old_bcrypt_verify(plain_password: str, hashed_password_db: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_db.encode('utf-8'))

def update_user_password_in_db(user_id: int, new_hash: str, db: Session) -> None:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.hashed_password = new_hash
        db.commit()

def check_and_migrate(user_id: int, plain_password: str, hashed_password_db: str, db: Session) -> bool:
    if hashed_password_db.startswith('$2b$') or hashed_password_db.startswith('$2a$'):
        if old_bcrypt_verify(plain_password, hashed_password_db):
            new_hash = get_password_hash(plain_password)
            update_user_password_in_db(user_id, new_hash, db)
            return True 
        return False 
    return verify_password(plain_password, hashed_password_db)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- LIFESPAN: Inizializzazione Database Sicura ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Proviamo a creare le tabelle. Se i modelli hanno micro-disallineamenti,
    # stampiamo l'errore senza far crashare l'intero container di Railway.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[CRITICAL] Errore durante la creazione delle tabelle: {e}")
        print("L'applicazione proverà comunque ad avviarsi per consentire la diagnostica.")

    db = SessionLocal()
    try:
        # Controllo superuser agnostico: cerchiamo se esiste ALMENO un utente admin
        admin_exists = db.query(models.User).filter(models.User.is_superuser == True).first()
        if not admin_exists:
            print("--- Inizializzazione: Creazione Super Admin di default ---")
            hashed_pw = get_password_hash("PasswordSicura123!")
            
            # Creiamo l'oggetto usando solo i campi strutturali minimi e universali
            nuovo_admin = models.User()
            nuovo_admin.email = "admin@tuosito.com"
            
            # Rileviamo dinamicamente come si chiama il campo password nel tuo models.py
            if hasattr(models.User, 'hashed_password'):
                nuovo_admin.hashed_password = hashed_pw
            elif hasattr(models.User, 'password'):
                nuovo_admin.password = hashed_pw
                
            nuovo_admin.is_superuser = True
            
            # Gestione dinamica del ruolo
            if hasattr(models.User, 'role'):
                nuovo_admin.role = "superadmin"
            elif hasattr(models.User, 'role_id'):
                nuovo_admin.role_id = 1
                
            db.add(nuovo_admin)
            db.commit()
            print("--- Super Admin creato con successo! ---")
    except Exception as e:
        print(f"[WARNING] Creazione Super Admin automatico fallita: {e}")
    finally:
        db.close()
    yield


# --- INIZIALIZZAZIONE APPLICAZIONE ---
app = FastAPI(
    title="Multi-Tenant Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- SCHEMI DATI ---
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

class SpaceCreateRequest(BaseModel):
    nome: str
    licenza_id: int
    tipo_spazio_id: int


# --- ROTTA DI AUTENTICAZIONE (LOGIN) ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email o password errati")
    
    if not check_and_migrate(user.id, form_data.password, user.hashed_password, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- ROTTE EX-ADMIN_SETUP.PY (INTEGRATE) ---
@app.get("/admin-setup/status")
def check_setup_status(db: Session = Depends(get_db)):
    try:
        from admin_service import AdminService
        return {"initialized": AdminService().is_initialized(db)}
    except Exception as e:
        return {"initialized": False, "error": str(e)}

@app.post("/admin-setup/create-space")
def create_space_setup(data: SpaceCreateRequest, db: Session = Depends(get_db)):
    try:
        from admin_service import AdminService
        spazio = AdminService().validate_license_and_create_space(
            db, data.nome, data.licenza_id, data.tipo_spazio_id
        )
        return {"message": "Spazio creato", "id": spazio.id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ROTTE SUPER ADMIN ---
@app.post("/superadmin/spazi", status_code=status.HTTP_201_CREATED)
def create_spazio(dati: SpazioCreate, db: Session = Depends(get_db)):
    try:
        scadenza = datetime.strptime(dati.data_scadenza_licenza, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido. Usa YYYY-MM-DD")
        
    nuovo_spazio = models.Spazio(nome=dati.nome, data_scadenza_licenza=scadenza)
    db.add(nuovo_spazio)
    db.commit()
    db.refresh(nuovo_spazio)
    return nuovo_spazio

@app.post("/superadmin/utenti", status_code=status.HTTP_201_CREATED)
def create_utente(dati: UserCreate, db: Session = Depends(get_db)):
    spazio = db.query(models.Spazio).filter(models.Spazio.id == dati.spazio_id).first()
    if not spazio:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
        
    user_exists = db.query(models.User).filter(models.User.email == dati.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email già registrata")
        
    hashed_pw = get_password_hash(dati.password)
    nuovo_utente = models.User(
        email=dati.email,
        hashed_password=hashed_pw,
        spazio_id=dati.spazio_id,
        role=str(dati.role_id)
    )
    db.add(nuovo_utente)
    db.commit()
    db.refresh(nuovo_utente)
    return {"id": nuovo_utente.id, "email": nuovo_utente.email}

@app.post("/superadmin/licenze", status_code=status.HTTP_201_CREATED)
def create_licenza(dati: LicenzaCreate, db: Session = Depends(get_db)):
    try:
        scadenza = datetime.strptime(dati.data_scadenza, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido. Usa YYYY-MM-DD")
        
    nuova_licenza = models.Licenza(
        intestatario=dati.intestatario,
        max_spazi=dati.max_spazi,
        max_utenti_totali=dati.max_utenti_totali,
        max_aziende_totali=dati.max_aziende_totali,
        data_scadenza=scadenza
    )
    db.add(nuova_licenza)
    db.commit()
    db.refresh(nuova_licenza)
    return nuova_licenza


# --- MIDDLEWARE DI CONTROLLO TENANT ---
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if len(host.split(".")) > 2 else None
    request.state.subdomain = subdomain
    response = await call_next(request)
    return response


# --- HEALTH CHECK ---
@app.get("/")
def read_root(request: Request):
    return {
        "status": "online",
        "detected_subdomain": request.state.subdomain,
        "message": "Backend Multi-Tenant centralizzato e attivo."
    }
