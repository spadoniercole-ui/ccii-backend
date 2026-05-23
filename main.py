import os
import base64
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Integer
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

# --- MODELLI DATABASE ESSENZIALI ---

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

# Evitiamo create_all globale se le tabelle esistono già o generano conflitti di tipo.
# Base.metadata.create_all(bind=engine)

# --- INIZIALIZZAZIONE FASTAPI ---
app = FastAPI(title="CCII Web API")

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
    return "<h3>Backend CCII attivo (Modalità Isolata)</h3>"

@app.get("/tenants")
def get_old_tenants(db: Session = Depends(get_db)):
    try:
        # Tentativo di lettura dal database reale
        record_spazi = db.query(Spazi).all()
        risposta_frontend = []
        for s in record_spazi:
            risposta_frontend.append({
                "id": str(s.id),
                "nome": s.nome,
                "codice": s.codice,
                "attivo": s.attivo,
                "nome_spazio": s.nome,
                "max_utenti": 5, 
                "max_aziende": 10
            })
        return risposta_frontend
    except Exception as e:
        # Fallback statico nel caso in cui le tabelle non siano accessibili
        return [
            {
                "id": "da39a3ee-5e6b-4b0d-bc12-456789abcdef",
                "nome": "Studio Demo",
                "codice": "DEMO01",
                "attivo": True,
                "nome_spazio": "Studio Demo Connesso",
                "max_utenti": 5,
                "max_aziende": 10
            }
        ]

@app.post("/login")
def login(req: LoginRequest):
    if req.username == "SuperAdmin" and req.password == "CCIIWeb2.0":
        fake_payload = {"role": "SUPER_ADMIN"}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
        return {"token": f"fakeHeader.{payload_b64}.fakeSignature"}
    raise HTTPException(status_code=401, detail="Credenziali errate")
