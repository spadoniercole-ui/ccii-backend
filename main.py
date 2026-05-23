import os
import base64
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
import uuid

# --- CONFIGURAZIONE DATABASE ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- TABELLE DI GIUNZIONE ---
moduli_tipi_spazio = Table(
    'moduli_tipi_spazio',
    Base.metadata,
    Column('tipo_spazio_id', UUID(as_uuid=True), ForeignKey('tipi_spazio.id', ondelete='CASCADE'), primary_key=True),
    Column('modulo_id', UUID(as_uuid=True), ForeignKey('moduli.id', ondelete='CASCADE'), primary_key=True)
)

permessi_utente_azienda = Table(
    'permessi_utente_azienda',
    Base.metadata,
    Column('utente_id', UUID(as_uuid=True), ForeignKey('utenti.id', ondelete='CASCADE'), primary_key=True),
    Column('azienda_id', UUID(as_uuid=True), ForeignKey('aziende.id', ondelete='CASCADE'), primary_key=True),
    Column('permesso', String(50), nullable=False)
)

autorizzazioni_modulo = Table(
    'autorizzazioni_modulo',
    Base.metadata,
    Column('utente_id', UUID(as_uuid=True), ForeignKey('utenti.id', ondelete='CASCADE'), primary_key=True),
    Column('modulo_id', UUID(as_uuid=True), ForeignKey('moduli.id', ondelete='CASCADE'), primary_key=True),
    Column('autorizzazione', String(50), nullable=False)
)

# --- MODELLI DATABASE REALINEATI ALLO SCHEMA SQL ---

class TipiSpazio(Base):
    __tablename__ = 'tipi_spazio'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(String, nullable=True)
    
    spazi = relationship("Spazi", back_populates="tipo_spazio")

class Spazi(Base):
    __tablename__ = 'spazi'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    codice = Column(String(50), unique=True, nullable=False)
    tipo_spazio_id = Column(UUID(as_uuid=True), ForeignKey('tipi_spazio.id'))
    logo_spazio = Column(String, nullable=True)
    attivo = Column(Boolean, default=True)
    
    tipo_spazio = relationship("TipiSpazio", back_populates="spazi")
    aziende = relationship("Aziende", back_populates="spazio", cascade="all, delete-orphan")
    utenti = relationship("Utenti", back_populates="spazio", cascade="all, delete-orphan")

class Moduli(Base):
    __tablename__ = 'moduli'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(String, nullable=True)
    attivo_globale = Column(Boolean, default=True)

class Aziende(Base):
    __tablename__ = 'aziende'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spazio_id = Column(UUID(as_uuid=True), ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    ragione_sociale = Column(String(500), nullable=False)
    partita_iva = Column(String(16), nullable=True)
    codice_fiscale = Column(String(16), nullable=True)
    codice_ateco = Column(String(10), nullable=True)
    attiva = Column(Boolean, default=True)
    
    spazio = relationship("Spazi", back_populates="aziende")

class Utenti(Base):
    __tablename__ = 'utenti'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spazio_id = Column(UUID(as_uuid=True), ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    tipologia = Column(String(50), nullable=False)
    licenza = Column(String(100), nullable=True)
    attivo = Column(Boolean, default=True)
    tentativi_login_falliti = Column(Integer, default=0)
    bloccato = Column(Boolean, default=False)
    
    spazio = relationship("Spazi", back_populates="utenti")

Base.metadata.create_all(bind=engine)

# --- INIZIALIZZAZIONE FASTAPI ---
app = FastAPI(title="CCII Web API - Allineamento Database")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginRequest(BaseModel):
    username: str
    password: str

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h3>Backend CCII attivo e allineato al DB PostgreSQL</h3>"

# 🟢 ROTTA /tenants INTEGRATA CON I CAMPI REALI DEL FRONTEND REACT
@app.get("/tenants")
def get_old_tenants(db: Session = Depends(get_db)):
    # Interroghiamo la tabella reale 'spazi'
    record_spazi = db.query(Spazi).all()
    
    risposta_frontend = []
    for s in record_spazi:
        # Calcoliamo i limiti o inseriamo valori di fallback coerenti
        risposta_frontend.append({
            "id": str(s.id),
            "nome": s.nome,
            "codice": s.codice,
            "attivo": s.attivo,
            # Forniamo chiavi stabili che il componente React cerca per evitare stringhe vuote o N/D
            "nome_spazio": s.nome,
            "max_utenti": 5, 
            "max_aziende": 10
        })
    return risposta_frontend

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if req.username == "SuperAdmin" and req.password == "CCIIWeb2.0":
        fake_payload = {"role": "SUPER_ADMIN"}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
        return {"token": f"fakeHeader.{payload_b64}.fakeSignature"}
    raise HTTPException(status_code=401, detail="Credenziali errate")
