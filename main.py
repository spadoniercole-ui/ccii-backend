from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Importazioni locali
# --- IMPORTAZIONI LOCALI CORRETTE (STRUTTURA IBRIDA) ---
from database import engine, Base, get_db, SessionLocal
import models  # Rimane così perché models.py è di fianco a main.py
from utils import get_password_hash
from dependencies import require_superadmin, get_current_user

# Questi due si trovano dentro la sotto-cartella 'app', quindi serve il prefisso:
from app.auth import check_and_migrate, create_access_token
from app.routes.admin_setup import router as admin_setup_router
from dependencies import require_superadmin, get_current_user
from app.auth import check_and_migrate, create_access_token
from app.routes.admin_setup import router as admin_setup_router

from utils import get_password_hash
from dependencies import require_superadmin, get_current_user
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

# --- 2. INIZIALIZZAZIONE APP ---
app = FastAPI(lifespan=lifespan)

# --- 3. MIDDLEWARE E ECCEZIONI ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Errore interno del sistema."},
    )

# --- 4. ROUTER ---
app.include_router(admin_setup_router)

@app.get("/")
def root():
    return {"status": "ok"}

# --- 5. AUTH E LOGIN ---

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Effettua il login e migra automaticamente la password se in vecchio formato.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # check_and_migrate gestisce la verifica e l'eventuale aggiornamento DB
    if not user or not check_and_migrate(user.id, form_data.password, user.password):
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
    admin: models.User = Depends(require_superadmin)
):
    data_scadenza = datetime.strptime(dati.data_scadenza_licenza, "%Y-%m-%d")
    nuovo_spazio = models.Spazio(nome=dati.nome, data_scadenza_licenza=data_scadenza)
    db.add(nuovo_spazio)
    db.commit()
    return {"status": "success", "id": nuovo_spazio.id}

# (Resto delle tue rotte rimane invariato...)
