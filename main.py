from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Importazioni locali piatte (stessa cartella di main.py)
from database import engine, Base, get_db, SessionLocal
import models
from utils import get_password_hash, verify_password

# --- CONFIGURAZIONE STRUTTURA DI FALLBACK JWT ---
SECRET_KEY = "CAMBIA_QUESTA_CHIAVE_SEGRETISSIMA_IN_PRODUZIONE"
ALGORITHM = "HS256"

def login_create_access_token(data: dict):
    from jose import jwt
    from datetime import timedelta
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- LIFESPAN: Inizializzazione Database ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_exists = db.query(models.User).filter(models.User.is_superuser == True).first()
        if not admin_exists:
            print("--- Inizializzazione: Creazione Super Admin di default ---")
            hashed_pw = get_password_hash("PasswordSicura123!")
            # Nota: usiamo i campi standard del tuo modello User
            nuovo_admin = models.User(
                email="admin@tuosito.com",
                hashed_password=hashed_pw,
                is_superuser=True,
                role="superadmin"
            )
            db.add(nuovo_admin)
            db.commit()
    except Exception as e:
        print(Log Inizializzazione Fallito: {e})
    finally:
        db.close()
    yield

# --- INIZIALIZZAZIONE APPLICAZIONE ---
app = FastAPI(
    title="Multi-Tenant Backend",
    version="1.0.0",
    lifespan=lifespan
)

# --- CONFIGURAZIONE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DIPENDENZE DI SICUREZZA INTERNE ---
def get_local_current_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    return user

def require_superadmin(current_user: models.User = Depends(get_local_current_user)):
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Accesso negato: permessi Super Admin insufficienti."
        )
    return current_user

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

# --- ROTTA DI AUTENTICAZIONE (LOGIN) ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # Controllo password sicuro e migrazione dinamica integrata senza file esterni
    if not user:
        raise HTTPException(status_code=401, detail="Email o password errati")
    
    # Verifica l'hash (compatibile sia con il vecchio bcrypt che con argon2 tramite utils)
    is_valid = False
    try:
        # Tenta la verifica Argon2 standard dal tuo file utils
        is_valid = verify_password(form_data.password, user.hashed_password)
    except Exception:
        # Fallback se l'hash memorizzato è il vecchio bcrypt string
        import bcrypt
        try:
            is_valid = bcrypt.checkpw(form_data.password.encode('utf-8'), user.hashed_password.encode('utf-8'))
            if is_valid:
                # Migra ad Argon2 sul momento
                user.hashed_password = get_password_hash(form_data.password)
                db.commit()
        except Exception:
            is_valid = False

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = login_create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ROTTE SUPER ADMIN ---

@app.post("/superadmin/spazi", status_code=status.HTTP_201_CREATED)
def create_spazio(
    dati: SpazioCreate, 
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
        hashed_password=hashed_pw,
        spazio_id=dati.spazio_id,
        role=str(dati.role_id)
    )
    db.add(nuovo_utente)
    db.commit()
    db.refresh(nuovo_utente)
    return {"id": nuovo_utente.id, "email": nuovo_utente.email}

@app.post("/superadmin/licenze", status_code=status.HTTP_201_CREATED)
def create_licenza(
    dati: LicenzaCreate, 
    db: Session = Depends(get_db)
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

# --- INCLUSIONE ROUTER DINAMICO PROTETTO ---
# Iniettiamo i percorsi direttamente per evitare i crash di importazione di Python delle sottocartelle
@app.get("/admin-setup/status")
def check_setup_status(db: Session = Depends(get_db)):
    try:
        from admin_service import AdminService
        return {"initialized": AdminService().is_initialized(db)}
    except Exception:
        return {"initialized": False, "note": "Servizio admin parzialmente caricato"}

# --- MIDDLEWARE DI CONTROLLO TENANT ---
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if len(host.split(".")) > 2 else None
    request.state.subdomain = subdomain
    response = await call_next(request)
    return response

# --- ROTTA DI VERIFICA (HEALTH CHECK) ---
@app.get("/")
def read_root(request: Request):
    return {
        "status": "online",
        "detected_subdomain": request.state.subdomain,
        "message": "Backend Multi-Tenant rigenerato e attivo."
    }
