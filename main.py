from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import re
import models
from database import get_db, engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CCII Platform - Analizzatore XBRL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UTILITY: ESTRATTORE ISTANTANEO ANNO E ANAGRAFICA ---
def analizza_basico_xbrl(xml_content: str) -> tuple:
    """
    Legge rapidamente il file per estrarre l'anno di riferimento e la denominazione.
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Cerca il tag della denominazione azienda
        azienda = "Non rilevata"
        for elem in root.findall(f".//{{*}}DatiAnagraficiDenominazione"):
            if elem.text:
                azienda = elem.text
                break
        
        # Identifica l'anno cercando i tag di chiusura esercizio nei contesti (es. 2024-12-31)
        anno = None
        date_trovate = re.findall(r'\d{4}-\d{2}-\d{2}', xml_content)
        if date_trovate:
            # Prende l'anno dalla prima data valida trovata (spesso la fine del periodo corrente)
            anno = int(date_trovate[0].split('-')[0])
            
        return azienda, anno
    except Exception:
        return "File non valido", None


# --- ENDPOINTS ---

@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Riceve l'XBRL, estrae i metadati chiave (Azienda, Anno) e registra la sequenza nel DB.
    """
    if not file.filename.endswith(('.xbrl', '.xml')):
        raise HTTPException(status_code=400, detail="Formato file non supportato.")
    
    try:
        content = await file.read()
        raw_text = content.decode('utf-8', errors='ignore')
        
        # Estrazione metadati per la griglia
        azienda, anno = analizza_basico_xbrl(raw_text)
        stato_validazione = "VALIDATED" if anno else "INVALID_STRUCTURE"
        
        nuovo_staging = models.XbrlStaging(
            filename=file.filename,
            raw_content=raw_text,
            azienda=azienda,
            anno_riferimento=anno,
            status=stato_validazione
        )
        
        db.add(nuovo_staging)
        db.commit()
        db.refresh(nuovo_staging)
        
        return {
            "status": "success",
            "staging_id": nuevo_staging.id,
            "filename": nuevo_staging.filename,
            "anno": anno,
            "azienda": azienda
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante il salvataggio: {str(e)}")


@app.get("/api/v1/analizzatore-xbrl")
def ottieni_cronologia_caricamenti(db: Session = Depends(get_db)):
    """
    Ritorna la lista dei caricamenti effettuati, ordinata cronologicamente 
    dal più recente. Alimenta la griglia del frontend.
    """
    try:
        storico = db.query(models.XbrlStaging).order_by(models.XbrlStaging.data_caricamento.desc()).all()
        return [
            {
                "id": voce.id,
                "filename": voce.filename,
                "azienda": voce.azienda or "N/D",
                "anno_riferimento": voce.anno_riferimento or "N/D",
                "stato": voce.status,
                "data_caricamento": voce.data_caricamento.strftime("%d/%m/%Y %H:%M:%S") if voce.data_caricamento else "N/D"
            }
            for voce in storico
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dello storico: {str(e)}")


@app.get("/")
def read_root():
    return {"status": "Sistema Analisi XBRL attivo"}
