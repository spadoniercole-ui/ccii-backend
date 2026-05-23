import os
import enum
import base64
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from passlib.context import CryptContext

# --- CONFIGURAZIONE SICUREZZA ---
# Configurazione per l'hashing sicuro delle password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONFIGURAZIONE DATABASE ---
# Railway fornisce l'URL nella variabile d'ambiente DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

# Gestione della stringa di connessione per SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- TABELLE DI GIUNZIONE (MANY-TO-MANY) ---
profilo_moduli = Table(
    'profilo_moduli',
    Base.metadata,
    Column('profilo_id', Integer, ForeignKey('profili_utente.id', ondelete='CASCADE'), primary_key=True),
    Column('modulo_id', Integer, ForeignKey('moduli_sistema.id', ondelete='CASCADE'), primary_key=True)
)

profilo_report = Table(
    'profilo_report',
    Base.metadata,
    Column('profilo_id', Integer, ForeignKey('profili_utente.id', ondelete='CASCADE'), primary_key=True),
    Column('report_id', Integer, ForeignKey('report_sistema.id', ondelete='CASCADE'), primary_key=True)
)

# --- ENUM RUOLI ---
class RuoloBaseEnum(enum.Enum):
    ADMIN_SPAZIO = "ADMIN_SPAZIO"
    OPERATORE = "OPERATORE"
    CONSULTATORE = "CONSULTATORE"

# --- MODELLI DATABASE ---
class Licenza(Base):
    __tablename__ = 'licenze'
    id = Column(Integer, primary_key=True, autoincrement=True)
    intestatario = Column(String, nullable=False)
    max_spazi = Column(Integer, default=1)
    max_utenti_totali = Column(Integer, default=3)
    max_aziende_totali = Column(Integer, default=3)
    data_scadenza = Column(Date, nullable=False)
    
    spazi = relationship("Spazio", back_populates="licenza")

class Spazio(Base):
    __tablename__ = 'spazi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    licenza_id = Column(Integer, ForeignKey('licenze.id', ondelete='RESTRICT'), nullable=False)
    nome_spazio = Column(String, nullable=False)
    tipologia = Column(String, nullable=False)
    
    licenza = relationship("Licenza", back_populates="spazi")
    utenti = relationship("Utente", back_populates="spazio")
    aziende = relationship("Azienda", back_populates="spazio")

class ModuloSistema(Base):
    __tablename__ = 'moduli_sistema'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String, unique=True, nullable=False)
    nome = Column(String, nullable=False)

class ReportSistema(Base):
    __tablename__ = 'report_sistema'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String, unique=True, nullable=False)
    nome = Column(String, nullable=False)

class ProfiloUtente(Base):
    __tablename__ = 'profili_utente'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_profilo = Column(String, nullable=False)
    
    moduli = relationship("ModuloSistema", secondary=profilo_moduli)
    report = relationship("ReportSistema", secondary=profilo_report)
    utenti = relationship("Utente", back_populates="profilo")

class Utente(Base):
    __tablename__ = 'utenti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    spazio_id = Column(Integer, ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    profilo_id = Column(Integer, ForeignKey('profili_utente.id', ondelete='SET NULL'), nullable=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    ruolo_base = Column(Enum(RuoloBaseEnum), nullable=False)
    tentativi_falliti = Column(Integer, default=0)
    
    spazio = relationship("Spazio", back_populates="utenti")
    profilo = relationship("ProfiloUtente", back_populates="utenti")

class Azienda(Base):
    __tablename__ = 'aziende'
    id = Column(Integer, primary_key=True, autoincrement=True)
    spazio_id = Column(Integer, ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    ragione_sociale = Column(String, nullable=False)
    partita_iva = Column(String(11), unique=True, nullable=False)
    codice_ateco = Column(String(6), nullable=False)
    attiva = Column(Boolean, default=True)
    
    spazio = relationship("Spazio", back_populates="aziende")

# Creazione effettiva delle tabelle all'avvio
Base.metadata.create_all(bind=engine)

# --- INIZIALIZZAZIONE FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dipendenza per ottenere la sessione del DB nelle rotte
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SCHEMI SCHEDE VALIDAZIONE (PYDANTIC) ---
class LoginRequest(BaseModel):
    username: str
    password: str

# --- ENDPOINT DI SERVIZIO ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- ENDPOINT LOGIN ---
@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Logica Hardcoded per il Super Admin a codice
    if req.username == "SuperAdmin":
        if req.password == "CCIIWeb2.0":
            fake_payload = {"role": "SUPER_ADMIN"}
            payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
            fake_token = f"fakeHeader.{payload_b64}.fakeSignature"
            return {"token": fake_token}
        else:
            raise HTTPException(status_code=401, detail="Credenziali errate")
    
    # Logica per gli utenti normali nel Database
    utente = db.query(Utente).filter(Utente.username == req.username).first()
    if not utente:
        raise HTTPException(status_code=401, detail="Utente non trovato")
        
    if utente.tentativi_falliti >= 5:
        raise HTTPException(status_code=403, detail="Account bloccato per troppi tentativi falliti")
        
    # Verifica della password con l'hash di bcrypt
    if not pwd_context.verify(req.password, utente.password_hash):
        utente.tentativi_falliti += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Credenziali errate")
        
    # Reset dei tentativi in caso di successo
    utente.tentativi_falliti = 0
    db.commit()
    
    # Generazione Token per utente dello spazio
    user_payload = {"role": utente.ruolo_base.value, "spazio_id": utente.spazio_id}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(user_payload).encode()).decode().rstrip("=")
    token = f"userHeader.{payload_b64}.userSignature"
    return {"token": token}

# --- ENDPOINT DI MOCK TEMPORANEO PER IL FRONTEND ---
@app.get("/tenants")
def get_tenants():
    return [
        {
            "id": "1",
            "name": "Studio Professionale Rossi (Test DB)",
            "type": "Studio Professionale",
            "max_users": 5,
            "max_companies": 10
        }
    ]
