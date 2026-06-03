import os
import sys
import bcrypt
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
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


# --- STRUTTURE E FUNZIONI HELPER PER PARSING XBRL (TUTTE LE TASSONOMIE IT-GAAP) ---
def individua_contesto_corrente(root) -> Optional[str]:
    """
    Scansiona i contesti del file XBRL alla ricerca dell'istanza dell'anno corrente.
    InfoCamere utilizza stringhe esplicite come 'c_corrente', 'c_01', 'comp_corrente'.
    """
    for elem in root.iter():
        if elem.tag.endswith('context') or elem.tag == 'context':
            ctx_id = elem.attrib.get('id', '')
            if 'corrente' in ctx_id or ctx_id == 'c_01':
                return ctx_id
                
    # Fallback: restituisce il primo ID valido se i pattern standard non corrispondono
    for elem in root.iter():
        if elem.tag.endswith('context') or elem.tag == 'context':
            ctx_id = elem.attrib.get('id')
            if ctx_id:
                return ctx_id
    return None

def estrai_anno_contesto(root, context_id: Optional[str]) -> str:
    """Estrae l'anno di riferimento testuale analizzando i tag temporali interni al contesto."""
    if not context_id:
        return str(datetime.now().year)
    for elem in root.iter():
        if elem.tag.endswith('context') or elem.tag == 'context':
            if elem.attrib.get('id') == context_id:
                for child in elem.iter():
                    if child.tag.endswith('instant') or child.tag.endswith('endDate'):
                        if child.text and len(child.text) >= 4:
                            return child.text[:4]
    return str(datetime.now().year)

def estrai_valore_it_gaap(root, tag_name: str, context_id: Optional[str]) -> float:
    """
    Cerca un tag specifico della tassonomia ignorando i namespace preposti (es. it-gaap:).
    Filtra rigorosamente per l'ID del contesto individuato per evitare duplicazioni storiche.
    """
    for elem in root.iter():
        if elem.tag.endswith(tag_name) or elem.tag == tag_name:
            if context_id and elem.attrib.get('contextRef') == context_id:
                try:
                    return float(elem.text)
                except (TypeError, ValueError):
                    continue
            elif not context_id: # Fallback se nessun contesto è isolabile
                try:
                    return float(elem.text)
                except (TypeError, ValueError):
                    continue
    return 0.0


# --- LIFESPAN: Inizializzazione Database Sicura ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Esegue la creazione tabelle isolando errori di compilazione/dialetto del DB
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[CRITICAL] Errore durante la creazione delle tabelle: {e}")
        print("L'applicazione proverà comunque ad avviarsi per consentire la diagnostica.")

    db = SessionLocal()
    try:
        admin_exists = db.query(models.User).filter(models.User.is_superuser == True).first()
        if not admin_exists:
            print("--- Inizializzazione: Creazione Super Admin di default ---")
            hashed_pw = get_password_hash("PasswordSicura123!")
            
            nuovo_admin = models.User()
            nuovo_admin.email = "admin@tuosito.com"
            
            # Controllo dinamico attributi password
            if hasattr(models.User, 'hashed_password'):
                nuovo_admin.hashed_password = hashed_pw
            elif hasattr(models.User, 'password'):
                nuovo_admin.password = hashed_pw
                
            nuovo_admin.is_superuser = True
            
            # Controllo dinamico attributi ruolo
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


# --- SCHEMI DATI COMPLETI ---
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

class SuperAdminWizardRequest(BaseModel):
    # Se valorizzato, indica che la licenza è già stata creata (trattativa commerciale)
    licenza_id: Optional[int] = None

class SuperAdminWizardRequest(BaseModel):
    username: str
    password: str
    intestatario_licenza: str
    max_spazi: int
    # ... altri campi veri della tua richiesta ...
    # CANCELLA la riga isolata che dice solo "admin_"
    
    # Step 1: Dati Licenza (Opzionali se licenza_id è presente)
    licenza_intestatario: Optional[str] = None
    licenza_max_spazi: Optional[int] = None
    licenza_max_utenti_totali: Optional[int] = None
    licenza_max_aziende_totali: Optional[int] = None
    licenza_data_scadenza: Optional[str] = None  # Formato YYYY-MM-DD
    
    # Step 2: Dati Primo Spazio (Tenant)
    spazio_nome: str
    spazio_tipo_id: int
        
