from fastapi import FastAPI
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
import models
from database import get_db

# --- INIZIALIZZAZIONE APP ---
app = FastAPI()

# --- SCHEMA ---
class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str

# --- ROUTE BASE (Test) ---
@app.get("/")
def read_root():
    return {"status": "ok"}

# --- ROUTE MODULO 8 ---
@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    nuovo_staging = models.XbrlStaging(
        filename=file.filename,
        raw_content=content.decode('utf-8', errors='ignore'),
        status="PENDING_VALIDATION"
    )
    db.add(nuovo_staging)
    db.commit()
    return {"status": "success", "staging_id": nuovo_staging.id}
