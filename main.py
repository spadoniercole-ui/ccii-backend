from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# Importiamo i componenti necessari dagli altri moduli del progetto 📦
from database import engine, Base, get_db
from models import Spazio

# Creiamo le tabelle nel database se non esistono ancora (utile su Railway) 🛠️
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestione Spazi API",
    description="API per la gestione delle licenze e degli spazi di lavoro",
    version="1.0.0"
)

# --- ROTTE DELL'APPLICAZIONE (ENDPOINTS) ---

# --- ROTTE DELL'APPLICAZIONE (ENDPOINTS) ---

@app.get("/")
def home():
    return {"status": "running", "message": "API Spazi funzionante correttamente"}

@app.get("/spazi/{spazio_id}")
def leggi_spazio(spazio_id: int, db: Session = Depends(get_db)):
    # Corretto: usiamo spazio_id per filtrare 🔍
    spazio = db.query(Spazio).filter(Spazio.id == spazio_id).first()
    
    if spazio is None:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
        
    return {
        "id": spazio.id,
        "licenza_id": spazio.licenza_id,
        "nome_spazio": spazio.nome_spazio,
        "tipologia": spazio.tipologia
    }
