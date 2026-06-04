from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import models
from database import get_db, engine, Base

# Configurazione speculare del DB: crea le tabelle all'avvio se mancanti
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CCII Platform - API Gateway")

# Middleware CORS per consentire le chiamate da Vercel/Locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

# --- SCHEMI DI VALIDAZIONE PYDANTIC (Conservati dal tuo impianto originale) ---
class LicenzaCreate(BaseModel):
    intestatario: str
    max_spazi: int
    max_utenti_totali: int
    max_aziende_totali: int
    data_scadenza: str


# --- UTILITY: PARSER NATIVO XBRL INFOCAMERE ---
def estrai_dati_xbrl(xml_content: str) -> dict:
    """
    Esegue il parsing dei nodi XML generati dai software di bilancio italiani.
    Mappa i contesti c0_i (Istantanea anno corrente) e c0_d (Durata anno corrente).
    """
    try:
        root = ET.fromstring(xml_content)
        
        def trova_valore(tag, context_ref=None):
            for elem in root.findall(f".//{{*}}{tag}"):
                if context_ref:
                    if elem.attrib.get('contextRef') == context_ref:
                        return elem.text
                else:
                    return elem.text
            return None

        # Estrazione Anagrafica
        denominazione = trova_valore('DatiAnagraficiDenominazione', 'c0_i')
        codice_fiscale = trova_valore('DatiAnagraficiCodiceFiscale', 'c0_i')
        partita_iva = trova_valore('DatiAnagraficiPartitaIva', 'c0_i')
        forma_giuridica = trova_valore('DatiAnagraficiFormaGiuridica', 'c0_i')
        
        # Estrazione Dati di Bilancio Monetari
        totale_attivo = trova_valore('TotaleAttivo', 'c0_i')
        patrimonio_netto = trova_valore('TotalePatrimonioNetto', 'c0_i')
        totale_debiti = trova_valore('TotaleDebiti', 'c0_i')
        ricavi = trova_valore('ValoreProduzioneRicaviVenditePrestazioni', 'c0_d')
        utile_perdita = trova_valore('UtilePerditaEsercizio', 'c0_d')

        return {
            "azienda": denominazione or "Non rilevata",
            "codice_fiscale": codice_fiscale or "Non rilevato",
            "partita_iva": partita_iva or "Non rilevata",
            "forma_giuridica": forma_giuridica or "Non rilevata",
            "metriche_chiave": {
                "totale_attivo": int(totale_attivo) if totale_attivo else 0,
                "patrimonio_netto": int(patrimonio_netto) if patrimonio_netto else 0,
                "totale_debiti": int(totale_debiti) if totale_debiti else 0,
                "ricavi_vendite": int(ricavi) if ricavi else 0,
                "utile_perdita_esercizio": int(utile_perdita) if utile_perdita else 0
            }
        }
    except Exception as e:
        return {"errore_parsing": f"Struttura XML non valida o non supportata: {str(e)}"}


# --- ENDPOINTS OPERATIVI ---

@app.post("/api/v1/analizzatore-xbrl")
async def ricevi_xbrl(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Riceve il file dal frontend, esegue il parsing dei dati vitali e popola 
    la tabella xbrl_staging su Railway impostando lo stato di validazione.
    """
    if not file.filename.endswith(('.xbrl', '.xml')):
        raise HTTPException(status_code=400, detail="Formato file non valido. Accettati solo .xbrl e .xml")
    
    try:
        content = await file.read()
        raw_text = content.decode('utf-8', errors='ignore')
        
        # Elaborazione immediata del contenuto
        analisi_risultato = estrai_dati_xbrl(raw_text)
        
        # Definizione dello stato in base al successo dell'estrazione
        stato_validazione = "VALIDATED" if "errore_parsing" not in analisi_risultato else "INVALID_STRUCTURE"
        
        # Scrittura su DB Postgres (Railway)
        nuovo_staging = models.XbrlStaging(
            filename=file.filename,
            raw_content=raw_text,
            status=stato_validazione
        )
        
        db.add(nuovo_staging)
        db.commit()
        db.refresh(nuovo_staging)
        
        return {
            "status": "success",
            "staging_id": nuovo_staging.id,
            "filename": nuovo_staging.filename,
            "stato_validazione": stato_validazione,
            "dati_complessivi": analisi_risultato
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nel caricamento a database: {str(e)}")


@app.get("/")
def read_root():
    return {
        "status": "Online",
        "modulo_xbrl": "Pronto",
        "ambiente": "Production/Railway Linked"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
