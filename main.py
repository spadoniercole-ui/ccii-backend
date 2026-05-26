from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from contextlib import asynccontextmanager

# --- IMPORTAZIONI LOCALI REALI E CHIARE ---
# Tutti questi file si trovano nella stessa cartella radice insieme a main.py
from database import engine, Base, get_db, SessionLocal
import models
from utils import get_password_hash
from dependencies import require_superadmin, get_current_user

# Questi due si trovano sotto la cartella 'app'
from app.auth import check_and_migrate, create_access_token
from app.routes.admin_setup import router as admin_setup_router


# --- 1. LIFESPAN: Gestione inizializzazione ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_exists = db.query(models.User).filter(models.User.is_superuser == True).first()
        if not admin_exists:
            print("--- Inizializzazione: Creazione Super Admin di default ---")
            hashed_pw = get_password_hash("PasswordSicura123!")
            nuovo_admin = models.User(
                email="admin@tuosito.com",
                password=hashed_pw,
                is_superuser=True
            )
            db.add(nuovo_admin)
            db.commit()
    finally:
        db.close()
    yield


# --- 2. INIZIALIZZAZIONE APPLICAZIONE ---
app = FastAPI(
    title="Multi-Tenant Backend",
    version="1.0.0",
    lifespan=lifespan
)


# --- 3. CONFIGURAZIONE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 4. INCLUSIONE ROUTER ESTERNI ---
app.include_router(admin_setup_router)


# --- 5. ROTTA DI AUTENTICAZIONE (LOGIN) ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # FIX APPLICATO: Passiamo 'db' come quarto parametro per permettere la migrazione dell'hash
    if not user or not check_and_migrate(user.id, form_data.password, user.password, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- 6. SCHEMI DATI ---
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


# --- 7. ROTTE SUPER ADMIN ---

@app.post("/superadmin/spazi", status_code=status.HTTP_201_CREATED)
def create_spazio(
    dati: SpazioCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(require_superadmin)
):
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
def create_utente(
    dati: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(require_superadmin)
):
    spazio = db.query(models.Spazio).filter(models.Spazio.id == dati.spazio_id).first()
    if not spazio:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
        
    user_exists = db.query(models.User).filter(models.User.email == dati.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Email già registrata")
        
    hashed_pw = get_password_hash(dati.password)
    nuovo_utente = models.User(
        email=dati.email,
        password=hashed_pw,
        spazio_id=dati.spazio_id,
        role_id=dati.role_id
    )
    db.add(nuovo_utente)
    db.commit()
    db.refresh(nuovo_utente)
    return {"id": nuovo_utente.id, "email": nuovo_utente.email}

@app.post("/superadmin/licenze", status_code=status.HTTP_201_CREATED)
def create_licenza(
    dati: LicenzaCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(require_superadmin)
):
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


# --- 8. MIDDLEWARE DI CONTROLLO TENANT (DIAGNOSTICA) ---
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if len(host.split(".")) > 2 else None
    request.state.subdomain = subdomain
    response = await call_next(request)
    return response


# --- 9. ROTTA DI VERIFICA (HEALTH CHECK) ---
@app.get("/")
def read_root(request: Request):
    return {
        "status": "online",
        "detected_subdomain": request.state.subdomain,
        "message": "Backend Multi-Tenant configurato correttamente."
    }
