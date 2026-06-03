import os
import bcrypt
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

# Importazioni locali
from database import engine, Base, get_db
import models

# --- INIZIALIZZAZIONE APP ---
app = FastAPI()

# --- MODELLI PYDANTIC PER VALIDAZIONE ---
class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str

# --- ENDPOINT ANALISI XBRL ---
@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Riceve il file XBRL, lo salva in staging e prepara la base per il parsing.
    """
    # 1. Validazione estensione
    if not file.filename.endswith(('.xbrl', '.xml')):
        raise HTTPException(status_code=400, detail="Formato file non supportato. Caricare file .xbrl o .xml")
    
    try:
        # 2. Lettura contenuto
        contenuto = await file.read()
        
        # 3. Salvataggio in database (Staging)
        nuovo_staging = models.XbrlStaging(
            filename=file.filename,
            raw_content=contenuto.decode('utf-8', errors='ignore'),
            status="STAGING"
        )
        db.add(nuovo_staging)
        db.commit()
        db.refresh(nuovo_staging)
        
        return {
            "status": "success",
            "message": "File ricevuto e in fase di staging",
            "staging_id": nuovo_staging.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante l'elaborazione: {str(e)}")

# --- LOGICA ESEMPIO CREAZIONE LICENZE ---
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

# --- MIDDLEWARE (Esempio) ---
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    # Logica di controllo tenant qui
    response = await call_next(request)
    return response

# Avvia l'applicazione (da lanciare solitamente via uvicorn)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
