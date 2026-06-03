import os
import sys
import bcrypt
from datetime import datetime, date
from typing import Optional

# -- IMPORTS ESSENZIALI --
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel  # Verifica che questa riga sia esattamente qui
from sqlalchemy.orm import Session

# -- DATABASE E MODELLI --
from database import engine, Base, get_db
import models

# -- CREAZIONE APP --
app = FastAPI()

# -- SCHEMA PYDANTIC --
# Se questo blocco fallisce, è perché il file precedente aveva errori di sintassi
# (es. parentesi non chiuse, indentazione errata nelle righe precedenti)
class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str

# -- ENDPOINT --
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

@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xbrl', '.xml')):
        raise HTTPException(status_code=400, detail="Formato file non supportato.")
    
    content = await file.read()
    nuovo_staging = models.XbrlStaging(
        filename=file.filename,
        raw_content=content.decode('utf-8', errors='ignore'),
        status="STAGING"
    )
    db.add(nuovo_staging)
    db.commit()
    return {"status": "success", "staging_id": nuovo_staging.id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
