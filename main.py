from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware  # <-- AGGIUNGI QUESTO
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import get_db, engine, Base

# Crea le tabelle nel DB se non esistono (utile per lo sviluppo)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- CONFIGURAZIONE CORS (AGGIUNGI QUESTO BLOCCO SUBITO SOTTO APP = FASTAPI()) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione sostituisci con l'URL esatto del frontend (es. ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],  # Permette POST, GET, OPTIONS, ecc.
    allow_headers=["*"],
)

# --- SCHEMA PER LA VALIDAZIONE ---
class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str

# --- ENDPOINT MODULO 8: INGESTION ---
@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Fase 1: Caricamento e salvataggio nello Staging.
    Il file viene salvato come stringa nel DB, permettendo di ritrovarlo
    nella lista dei file importati.
    """
    if not file.filename.endswith(('.xbrl', '.xml')):
        raise HTTPException(status_code=400, detail="Formato file non supportato.")
    
    try:
        # Legge il contenuto del file
        content = await file.read()
        
        # Salva nel modello XbrlStaging definito in models.py
        nuovo_staging = models.XbrlStaging(
            filename=file.filename,
            raw_content=content.decode('utf-8', errors='ignore'),
            status="PENDING_VALIDATION"
        )
        
        db.add(nuovo_staging)
        db.commit()
        db.refresh(nuovo_staging)
        
        return {
            "status": "success",
            "message": "File caricato correttamente",
            "staging_id": nuovo_staging.id,
            "filename": nuovo_staging.filename
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante il salvataggio: {str(e)}")

# --- TEST ROUTE ---
@app.get("/")
def read_root():
    return {"status": "Sistema Analisi XBRL attivo"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
