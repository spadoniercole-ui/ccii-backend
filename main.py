import os
import base64
import json
from datetime import date
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # 👈 Importato per servire la pagina HTML
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from passlib.context import CryptContext

# --- CONFIGURAZIONE SICUREZZA ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONFIGURAZIONE DATABASE ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
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

# --- MODELLI DATABASE ---

# [SISTEMA]
class Licenza(Base):
    __tablename__ = 'licenze'
    id = Column(Integer, primary_key=True, autoincrement=True)
    intestatario = Column(String, nullable=False)
    max_spazi = Column(Integer, default=1)
    max_utenti_totali = Column(Integer, default=3)
    max_aziende_totali = Column(Integer, default=3)
    data_scadenza = Column(Date, nullable=False)
    
    spazi = relationship("Spazio", back_populates="licenza", cascade="all, delete-orphan")

# [ANAGRAFICHE]
class Spazio(Base):
    __tablename__ = 'spazi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    licenza_id = Column(Integer, ForeignKey('licenze.id', ondelete='RESTRICT'), nullable=False)
    nome_spazio = Column(String, nullable=False)
    tipologia = Column(String, nullable=False)
    
    licenza = relationship("Licenza", back_populates="spazi")
    utenti = relationship("Utente", back_populates="spazio", cascade="all, delete-orphan")
    aziende = relationship("Azienda", back_populates="spazio", cascade="all, delete-orphan")

class ModuloSistema(Base):
    __tablename__ = 'moduli_sistema'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String, unique=True, nullable=False)
    nome = Column(String, nullable=False)

# [CONFIGURAZIONI]
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

# [TABELLE] Gestione dinamica dei ruoli
class TipologiaUtente(Base):
    __tablename__ = 'tipologie_utente'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice_ruolo = Column(String, unique=True, nullable=False)  # Es. 'ADMIN_SPAZIO'
    nome_ruolo = Column(String, nullable=False)                # Es. 'Amministratore Spazio'
    descrizione = Column(String, nullable=True)

    utenti = relationship("Utente", back_populates="tipologia")

# [ANAGRAFICHE] Collegata a Spazi, Profili e Tipologie
class Utente(Base):
    __tablename__ = 'utenti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    spazio_id = Column(Integer, ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    profilo_id = Column(Integer, ForeignKey('profili_utente.id', ondelete='SET NULL'), nullable=True)
    tipologia_id = Column(Integer, ForeignKey('tipologie_utente.id', ondelete='RESTRICT'), nullable=False)
    
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tentativi_falliti = Column(Integer, default=0)
    
    spazio = relationship("Spazio", back_populates="utenti")
    profilo = relationship("ProfiloUtente", back_populates="utenti")
    tipologia = relationship("TipologiaUtente", back_populates="utenti")

class Azienda(Base):
    __tablename__ = 'aziende'
    id = Column(Integer, primary_key=True, autoincrement=True)
    spazio_id = Column(Integer, ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    ragione_sociale = Column(String, nullable=False)
    partita_iva = Column(String(11), unique=True, nullable=False)
    codice_ateco = Column(String(6), nullable=False)
    attiva = Column(Boolean, default=True)
    
    spazio = relationship("Spazio", back_populates="aziende")

# [CONFIGURAZIONI]
class ConfigIndice(Base):
    __tablename__ = 'config_indici'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice_indice = Column(String, unique=True, nullable=False)
    nome_indice = Column(String, nullable=False)
    
    soglie = relationship("SogliaIndice", back_populates="indice", cascade="all, delete-orphan")

class SogliaIndice(Base):
    __tablename__ = 'soglie_indici'
    id = Column(Integer, primary_key=True, autoincrement=True)
    indice_id = Column(Integer, ForeignKey('config_indici.id', ondelete='CASCADE'), nullable=False)
    codice_ateco_settore = Column(String(6), nullable=False)
    valore_soglia = Column(String, nullable=False)
    operatore_confronto = Column(String, default='<')
    
    indice = relationship("ConfigIndice", back_populates="soglie")

# Creazione tabelle automatiche
Base.metadata.create_all(bind=engine)

# --- INIZIALIZZAZIONE FASTAPI ---
app = FastAPI(title="CCII Web API - Super Admin Dashboard")

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

# --- SCHEMI PYDANTIC ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TipologiaUtenteCreate(BaseModel):
    codice_ruolo: str = Field(..., example="OPERATORE")
    nome_ruolo: str = Field(..., example="Operatore standard")
    descrizione: str = None

class LicenzaCreate(BaseModel):
    intestatario: str = Field(..., example="Studio Commercialista")
    max_spazi: int = Field(..., gte=1)
    max_utenti_totali: int = Field(..., gte=1)
    max_aziende_totali: int = Field(..., gte=1)
    data_scadenza: date

# --- ENDPOINTS INTERFACCIA E API ---

@app.get("/", response_class=HTMLResponse)
def home():
    # Iniettiamo direttamente il nuovo codice con la barra laterale scura
    return """
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <title>Super Admin Dashboard - CCII Web 2.0</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-50 text-slate-800 font-sans b-block">
        <div class="p-8">
            <h1 class="text-2xl font-bold text-indigo-600">Nuova Dashboard HARDCODED</h1>
            <p class="text-sm text-slate-600 mt-2">Se vedi questa scritta, il backend si è aggiornato correttamente!</p>
        </div>
    </body>
    </html>
    """
# 1. Configurazione Menu Dashboard Super Admin
@app.get("/superadmin/menu")
def get_superadmin_menu():
    return {
        "ANAGRAFICHE": ["Anagrafica utenti", "Anagrafica spazi"],
        "COLLEGAMENTI": ["Configurazione XBRL", "Configurazione ISTAT"],
        "CONFIGURAZIONI": ["Check list", "Indici", "Report"],
        "TABELLE": ["Tipologia utente"],
        "SISTEMA": ["Profilo XBRL", "Licenze"]
    }

# 2. TABELLE ➡️ Inserimento Tipologia Utente
@app.post("/superadmin/tipologie-utente")
def create_tipologia_utente(req: TipologiaUtenteCreate, db: Session = Depends(get_db)):
    esistente = db.query(TipologiaUtente).filter(TipologiaUtente.codice_ruolo == req.codice_ruolo).first()
    if esistente:
        raise HTTPException(status_code=400, detail="Codice ruolo già registrato nel database")
    
    nuova_tipologia = TipologiaUtente(
        codice_ruolo=req.codice_ruolo,
        nome_ruolo=req.nome_ruolo,
        descrizione=req.descrizione
    )
    db.add(nuova_tipologia)
    db.commit()
    db.refresh(nuova_tipologia)
    return {"status": "success", "id": nuova_tipologia.id}

# 3. SISTEMA ➡️ Inserimento Licenze
@app.post("/superadmin/licenze")
def create_licenza(req: LicenzaCreate, db: Session = Depends(get_db)):
    if req.data_scadenza <= date.today():
        raise HTTPException(status_code=400, detail="La data di scadenza della licenza deve essere futura")
        
    nuova_licenza = Licenza(
        intestatario=req.intestatario,
        max_spazi=req.max_spazi,
        max_utenti_totali=req.max_utenti_totali,
        max_aziende_totali=req.max_aziende_totali,
        data_scadenza=req.data_scadenza
    )
    db.add(nuova_licenza)
    db.commit()
    db.refresh(nuova_licenza)
    return {"status": "success", "id": nuova_licenza.id}

# 4. Autenticazione (Login)
@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if req.username == "SuperAdmin":
        if req.password == "CCIIWeb2.0":
            fake_payload = {"role": "SUPER_ADMIN"}
            payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
            fake_token = f"fakeHeader.{payload_b64}.fakeSignature"
            return {"token": fake_token}
        else:
            raise HTTPException(status_code=401, detail="Credenziali errate")
    
    utente = db.query(Utente).filter(Utente.username == req.username).first()
    if not utente:
        raise HTTPException(status_code=401, detail="Utente non trovato")
        
    if utente.tentativi_falliti >= 5:
        raise HTTPException(status_code=403, detail="Account bloccato per motivi di sicurezza")
        
    if not pwd_context.verify(req.password, utente.password_hash):
        utente.tentativi_falliti += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Credenziali errate")
        
    utente.tentativi_falliti = 0
    db.commit()
    
    user_payload = {"role": utente.tipologia.codice_ruolo, "spazio_id": utente.spazio_id}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(user_payload).encode()).decode().rstrip("=")
    token = f"userHeader.{payload_b64}.userSignature"
    return {"token": token}
