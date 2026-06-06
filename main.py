from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import re
import models
from database import get_db, engine, Base
# --- INCOLLA QUI SUBITO DOPO GLI IMPORT DEL FILE ---

import xml.etree.ElementTree as ET
from typing import Dict, Any, List

def estrai_valore_xbrl(root: ET.Element, local_name: str, anno_riferimento: str) -> float:
    # ... (tutto il codice della funzione fornito sopra) ...

def estrai_anagrafica_xbrl(root: ET.Element, local_name: str) -> str:
    # ... (tutto il codice della funzione fornito sopra) ...

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
@router.post("/analizzatore-xbrl")
async def upload_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    
    # 1. Il tuo codice attuale che legge il file (NON TOCCARLO)
    file_bytes = await file.read()
    
    # 2. Il tuo codice attuale che inserisce il record nello Staging DB (NON TOCCARLO)
    # Esempio: new_staging = db.add(StagingXbrl(...))
    # Esempio: staging_id = new_staging.id
    staging_id = 28 # <--- Usa la tua variabile reale che recupera l'ID appena generato
    
    # =========================================================================
    # 3. PUNTO DI INSERIMENTO: ELABORAZIONE MATEMATICA
    # =========================================================================
    try:
        # Chiamiamo la funzione che estrae i tag veri e calcola gli indici
        risultato_completo = elabora_pipeline_xbrl(file_bytes, file.filename, staging_id)
        
        # Se vuoi persistere i dati calcolati anche nelle tue tabelle (es. tb_indici),
        # questo è il punto in cui farlo usando i valori dentro 'risultato_completo'
        
        # 4. RITORNA IL PAYLOAD COMPLETO AL FRONTEND
        return resultado_completo

    except Exception as e:
        return {"status": "error", "message": f"Errore elaborazione: {str(e)}"}
    
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
            "staging_id": nuovo_staging.id,       # <-- CORRETTO CON LA 'O'
            "filename": nuovo_staging.filename,   # <-- CORRETTO CON LA 'O'
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
