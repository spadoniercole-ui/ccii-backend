from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi import APIRouter
from app.routes import router as main_router
import xml.etree.ElementTree as ET
import models
import re  # <-- CORRETTO: Fondamentale per far funzionare re.findall

from database import get_db, engine, Base
from typing import Dict, Any, List

# --- UTILITY DI ESTRAZIONE XBRL ---

def estrai_valore_xbrl(root: ET.Element, local_name: str, anno_riferimento: str) -> float:
    """Estrae il valore numerico di un tag XBRL filtrando per local-name e anno nel contextRef."""
    for elem in root.iter():
        if elem.tag.split('}')[-1] == local_name:
            context_ref = elem.attrib.get('contextRef', '')
            if str(anno_riferimento) in context_ref:
                try:
                    return float(elem.text.strip()) if elem.text else 0.0
                except ValueError:
                    continue
    return 0.0

def estrai_anagrafica_xbrl(root: ET.Element, local_name: str) -> str:
    """Estrae il testo di un tag anagrafico XBRL filtrando per local-name."""
    for elem in root.iter():
        if elem.tag.split('}')[-1] == local_name:
            return elem.text.strip() if elem.text else ""
    return ""

def analizza_basico_xbrl(xml_content: str) -> tuple:
    """
    Legge rapidamente il file per estrarre l'anno di riferimento e la denominazione.
    """
    try:
        root = ET.fromstring(xml_content)
        azienda = "Non rilevata"
        
        # Uso iter() che è più robusto con i namespace rispetto a findall
        for elem in root.iter():
            if elem.tag.split('}')[-1] == "DatiAnagraficiDenominazione":
                if elem.text:
                    azienda = elem.text.strip()
                    break
        
        anno = None
        date_trovate = re.findall(r'\d{4}-\d{2}-\d{2}', xml_content)
        if date_trovate:
            anno = int(date_trovate[0].split('-')[0])
            
        return azienda, anno
    except Exception:
        return "File non valido", None


# --- INIZIALIZZAZIONE APPLICAZIONE ---

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione Router
app.include_router(main_router)
router = APIRouter()
app.include_router(router, prefix="/api/v1")

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],            
)


# --- ENDPOINTS ---

@app.post("/api/v1/analizzatore-xbrl")
@app.post("/analizzatore-xbrl")
async def upload_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # 1. Leggi il contenuto del file una sola volta
        file_bytes = await file.read()
        raw_text = file_bytes.decode('utf-8', errors='ignore')
        
        # 2. Estrazione al volo di azienda e anno per la griglia
        azienda, anno = analizza_basico_xbrl(raw_text)
        stato_validazione = "VALIDATED" if anno else "INVALID_STRUCTURE"
        
        # 3. Salvataggio IMMEDIATAMENTE nel database (genera l'ID reale)
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
        
        # 4. Elaborazione Pipeline (se la funzione è importata o disponibile)
        # Nota: Se 'elabora_pipeline_xbrl' non è ancora definita nel progetto, 
        # il blocco try-except intercetta l'errore senza spaccare il salvataggio.
        try:
            if 'elabora_pipeline_xbrl' in globals():
                risultato_completo = elabora_pipeline_xbrl(file_bytes, file.filename, nuovo_staging.id)
                return risultato_completo
        except Exception as e:
            # Se la matematica fallisce, salviamo comunque lo staging e avvisiamo il front-end
            nuovo_staging.status = "PROCESSING_ERROR"
            db.commit()
            return {
                "status": "partial_success",
                "message": f"File salvato ma calcolo indici fallito: {str(e)}",
                "staging_id": nuovo_staging.id,
                "filename": nuovo_staging.filename,
                "anno": anno,
                "azienda": azienda
            }

        # 5. Ritorno standard di successo (Alimenta direttamente la griglia)
        return {
            "status": "success",
            "staging_id": nuovo_staging.id,
            "filename": nuovo_staging.filename,
            "anno": anno,
            "azienda": azienda
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore critico del server: {str(e)}")


@app.get("/api/v1/analizzatore-xbrl")
def ottieni_cronologia_caricamenti(db: Session = Depends(get_db)):
    """
    Ritorna la lista dei caricamenti effettuati, ordinata cronologicamente.
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
