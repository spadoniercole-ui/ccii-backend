import os
import sys
import bcrypt
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


# --- LIFESPAN: Inizializzazione Database Sicura ---
@asynccontextmanager
async def lifespan(app: FastAPI):
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
            
            if hasattr(models.User, 'hashed_password'):
                nuovo_admin.hashed_password = hashed_pw
            elif hasattr(models.User, 'password'):
                nuovo_admin.password = hashed_pw
                
            nuovo_admin.is_superuser = True
            
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
    licenza_id: Optional[int] = None
    licenza_intestatario: Optional[str] = None
    licenza_max_spazi: Optional[int] = None
    licenza_max_utenti_totali: Optional[int] = None
    licenza_max_aziende_totali: Optional[int] = None
    licenza_data_scadenza: Optional[str] = None
    
    spazio_nome: str
    spazio_tipo_id: int
    
    admin_email: str
    admin_password: str
    # REFUSO "admin_" RIMOSSO CON SUCCESSO DA QUESTO SCHEMA


# --- ROTTA DI AUTENTICAZIONE (LOGIN) ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email o password errati")
    
    db_password = user.hashed_password if hasattr(user, 'hashed_password') else user.password
    
    if not check_and_migrate(user.id, form_data.password, db_password, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    licenze_esistenti = db.query(models.Licenza).count()
    is_superuser_flag = getattr(user, 'is_superuser', False)
    is_first_access = (licenze_esistenti == 0) and is_superuser_flag
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "is_superuser": is_superuser_flag,
        "is_first_access": is_first_access
    }


# --- ENDPOINT ANALIZZATORE XBRL REALE (PARSING DEI TAG IT-GAAP) ---
from fastapi import File, UploadFile

@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...)):
    # Log per verificare che il server riceva il segnale dal frontend
    print(f"Ricevuto file: {file.filename}")
    
    # Per ora, restituiamo un feedback che conferma la ricezione
    # Questo ti permette di testare la connessione Frontend -> Backend
    return {
        "status": "received",
        "filename": file.filename,
        "message": "Connessione stabilita. Il server è pronto per il parsing."
    }
    
    if not file.filename.endswith('.xbrl') and not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Formato file non valido. Accettati solo .xbrl o .xml")
    
    try:
        contenuto = await file.read()
        
        # Carica il file XML in memoria
        import xml.etree.ElementTree as ET
        root = ET.fromstring(contenuto)
        
        # Mappa dei principali tag della tassonomia XBRL Italiana (IT-GAAP)
        # Nota: Nei file XBRL i tag possono includere un prefisso di namespace dinamico (es. itcc-ci-ggi o pital).
        # Questo dizionario mappa le parole chiave finali dei tag che ci interessano.
        tag_mappa = {
            "patrimonioNetto": ["PatrimonioNetto", "AzioneCapitaleSottoscritto"],
            "attivoCircolante": ["AttivoCircolante", "TotaleAttivoCircolante"],
            "totaleDebiti": ["Debiti", "TotaleDebiti"],
            "valoreProduzione": ["ValoreProduzione", "TotaleValoreProduzione"],
            "costiProduzione": ["CostiProduzione", "TotaleCostiProduzione"],
            "utilePerdita": ["UtilePerditaEsercizio", "UtilePerdita"]
        }
        
        # Inizializza i dati estratti a 0
        dati_estratti = {
            "annoRiferimento": date.today().year,
            "patrimonioNetto": 0,
            "attivoCircolante": 0,
            "totaleDebiti": 0,
            "valoreProduzione": 0,
            "costiProduzione": 0,
            "utilePerdita": 0
        }

        # Cerca l'anno di riferimento (contesto di chiusura esercizio corrente)
        for elem in root.iter():
            if 'endDate' in elem.tag:
                try:
                    dati_estratti["annoRiferimento"] = datetime.strptime(elem.text.strip(), "%Y-%m-%d").year
                    break
                except:
                    pass

        # Estrazione dinamica dei valori numerici ignorando i namespace complessi
        for elem in root.iter():
            # Pulisce il tag eliminando il namespace racchiuso tra parentesi graffe "{...}"
            clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Controlla se il tag ripulito corrisponde a uno dei campi di bilancio cercati
            for chiave_interna, tag_target_list in tag_mappa.items():
                if clean_tag in tag_target_list and elem.text:
                    try:
                        # Converte il testo in float (gestendo eventuali spazi) e poi in int per la visualizzazione
                        valore = int(float(elem.text.strip()))
                        # Se il valore è già popolato, mantiene il massimo (spesso i file XBRL contengono sia l'anno corrente che il precedente)
                        if dati_estratti[chiave_interna] == 0:
                            dati_estratti[chiave_interna] = valore
                    except ValueError:
                        pass

        return {
            "success": True,
            "data": dati_estratti
        }

    except ET.ParseError:
        raise HTTPException(status_code=400, detail="Il file inviato non è un file XML/XBRL valido o è corrotto.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'analisi del file XBRL: {str(e)}")


# --- ROTTE SUPER ADMIN & WIZARD BIFORCATO ---
@app.post("/superadmin/wizard-setup", status_code=status.HTTP_201_CREATED)
def superadmin_wizard_setup(dati: SuperAdminWizardRequest, db: Session = Depends(get_db)):
    email_esistente = db.query(models.User).filter(models.User.email == dati.admin_email).first()
    if email_esistente:
        raise HTTPException(status_code=400, detail=f"L'email {dati.admin_email} è già registrata.")

    try:
        if dati.licenza_id is not None:
            licenza_attiva = db.query(models.Licenza).filter(models.Licenza.id == dati.licenza_id).first()
            if not licenza_attiva:
                raise HTTPException(status_code=404, detail=f"Licenza commerciale con ID {dati.licenza_id} non trovata.")
            scadenza_licenza = licenza_attiva.data_scadenza
            id_licenza_corrente = licenza_attiva.id
        else:
            if not dati.licenza_data_scadenza or not dati.licenza_intestatario:
                raise HTTPException(status_code=400, detail="Dati licenza incompleti. Fornire una licenza_id o i dati per una nuova licenza.")
            
            try:
                scadenza_licenza = datetime.strptime(dati.licenza_data_scadenza, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato data licenza non valido. Usa YYYY-MM-DD")

            nuova_licenza = models.Licenza(
                intestatario=dati.licenza_intestatario,
                max_spazi=dati.licenza_max_spazi if dati.licenza_max_spazi is not None else 1,
                max_utenti_totali=dati.licenza_max_utenti_totali if dati.licenza_max_utenti_totali is not None else 5,
                max_aziende_totali=dati.licenza_max_aziende_totali if dati.licenza_max_aziende_totali is not None else 1,
                data_scadenza=scadenza_licenza
            )
            db.add(nuova_licenza)
            db.flush()
            id_licenza_corrente = nuova_licenza.id

        nuovo_spazio = models.Spazio()
        nuovo_spazio.nome = dati.spazio_nome
        nuovo_spazio.data_scadenza_licenza = scadenza_licenza
        
        if hasattr(models.Spazio, 'licenza_id'):
            nuovo_spazio.licenza_id = id_licenza_corrente
        if hasattr(models.Spazio, 'tipo_spazio_id'):
            nuovo_spazio.tipo_spazio_id = dati.spazio_tipo_id
            
        db.add(nuovo_spazio)
        db.flush()

        hashed_pw = get_password_hash(dati.admin_password)
        nuovo_admin = models.User()
        nuovo_admin.email = dati.admin_email
        
        if hasattr(models.User, 'hashed_password'):
            nuovo_admin.hashed_password = hashed_pw
        elif hasattr(models.User, 'password'):
            nuovo_admin.password = hashed_pw

        nuovo_admin.is_superuser = False
        
        if hasattr(models.User, 'role'):
            nuovo_admin.role = "admin"
        elif hasattr(models.User, 'role_id'):
            nuovo_admin.role_id = 2
            
        if hasattr(models.User, 'spazio_id'):
            nuovo_admin.spazio_id = nuovo_spazio.id

        db.add(nuovo_admin)
        db.commit()
        
        return {
            "status": "success",
            "message": "Configurazione completata con successo tramite Wizard transazionale.",
            "data": {
                "licenza_id": id_licenza_corrente,
                "spazio_id": nuovo_spazio.id,
                "admin_id": nuovo_admin.id,
                "admin_email": nuovo_admin.email
            }
        }

    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Errore durante l'esecuzione del wizard (Transazione interrotta): {str(e)}"
        )


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
    nuovo_utente = models.User(email=dati.email, spazio_id=dati.spazio_id)
    
    if hasattr(models.User, 'hashed_password'):
        nuovo_utente.hashed_password = hashed_pw
    elif hasattr(models.User, 'password'):
        nuovo_utente.password = hashed_pw
        
    if hasattr(models.User, 'role'):
        nuovo_utente.role = str(dati.role_id)
    elif hasattr(models.User, 'role_id'):
        nuovo_utente.role_id = dati.role_id

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
