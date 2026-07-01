from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, List

app = FastAPI()
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DIZIONARIO MASTER STRUTTURALE (12 PARAMETRI TARGET) ---
PARAMETRI_PARIFICAZIONE = [
    {"categoria": "REDDITIVITÀ", "indice_target": "ROE", "parametro_logico": "Utile Netto", "tag_master": "it-cc-ci_UtilePerditaEsercizio", "tag_clean": "utileperditaesercizio"},
    {"categoria": "REDDITIVITÀ", "indice_target": "ROE", "parametro_logico": "Patrimonio Netto", "tag_master": "it-cc-ci_PatrimonioNetto", "tag_clean": "patrimonionetto"},
    {"categoria": "REDDITIVITÀ", "indice_target": "ROI / ROS", "parametro_logico": "Risultato Operativo (EBIT)", "tag_master": "it-cc-ci_DifferenzaValoreCostiProduzione", "tag_clean": "differenzavalorecostiproduzione"},
    {"categoria": "REDDITIVITÀ", "indice_target": "ROI / ROA", "parametro_logico": "Totale Attivo", "tag_master": "it-cc-ci_TotaleAttivoPassivo", "tag_clean": "totaleattivopassivo"},
    {"categoria": "REDDITIVITÀ", "indice_target": "ROS / EBITDA %", "parametro_logico": "Ricavi delle Vendite", "tag_master": "it-cc-ci_RicaviVenditePrestazioni", "tag_clean": "ricavivenditeprestazioni"},
    {"categoria": "LIQUIDITÀ", "indice_target": "Current / Quick Ratio", "parametro_logico": "Attivo Corrente", "tag_master": "it-cc-ci_AttivoCircolanteTotale", "tag_clean": "attivocircolantetotale"},
    {"categoria": "LIQUIDITÀ", "indice_target": "Current / Quick Ratio", "parametro_logico": "Passivo Corrente", "tag_master": "it-cc-ci_DebitiEsigibiliEntroEsercizio", "tag_clean": "debitiesigibilientroesercizio"},
    {"categoria": "LIQUIDITÀ", "indice_target": "Quick Ratio", "parametro_logico": "Rimanenze", "tag_master": "it-cc-ci_RimanenzeTotale", "tag_clean": "rimanenzetotale"},
    {"categoria": "SOLIDITÀ", "indice_target": "Leverage", "parametro_logico": "Totale Debiti", "tag_master": "it-cc-ci_DebitiTotale", "tag_clean": "debititotale"},
    {"categoria": "SOLIDITÀ", "indice_target": "Copertura Immobilizzazioni", "parametro_logico": "Immobilizzazioni", "tag_master": "it-cc-ci_ImmobilizzazioniTotale", "tag_clean": "immobilizzazionitotale"},
    {"categoria": "CCII_CRISI", "indice_target": "DSCR / Cash Flow", "parametro_logico": "Ammortamenti e Svalutazioni", "tag_master": "it-cc-ci_AmmortamentiSvalutazioniTotale", "tag_clean": "ammortamentisvalutazionitotale"},
    {"categoria": "CCII_CRISI", "indice_target": "DSCR / Cash Flow", "parametro_logico": "Accantonamenti", "tag_master": "it-cc-ci_AccantonamentiPerRischiOneri", "tag_clean": "accantonamentiperrischioneri"}
]

def clean_tag_name(tag: str) -> str:
    if not tag: return ""
    s = tag.split('}')[-1]
    s = re.sub(r'^(it-cc-ci_|itcc-ci_|itcc-ci:|xbrli:|it-cc-ci:)', '', s, flags=re.IGNORECASE)
    return s.strip()

def estrai_universo_tag(root: ET.Element) -> List[Dict[str, Any]]:
    """ Scansiona ed estrae integralmente ogni tag numerico valido presente nel file XBRL """
    tag_scoperti = []
    visti = set()
    contatore = 1
    
    tag_esclusi = ['xbrl', 'context', 'unit', 'schemaRef', 'identifier', 'segment', 'period', 'startDate', 'endDate', 'instant']
    
    for elem in root.iter():
        tag_raw = elem.tag.split('}')[-1]
        if tag_raw in tag_esclusi or not elem.text or not elem.text.strip():
            continue
            
        context_ref = elem.attrib.get('contextRef', '')
        # Intercettiamo i contesti di bilancio (corrente c0, precedente c1 o varianti standard)
        if any(c in context_ref for c in ['c0', 'c1', 'Instant', 'Duration']):
            valore_str = elem.text.strip()
            # Validiamo che sia un dato numerico (importi o conteggi)
            if re.match(r'^-?\d+(\.\d+)?$', valore_str):
                chiave = f"{tag_raw}_{context_ref}_{valore_str}"
                if chiave not in visti:
                    visti.add(chiave)
                    tag_scoperti.append({
                        "id_veloce": f"T{contatore}",
                        "tag_reale": tag_raw,
                        "contesto": context_ref,
                        "valore": float(valore_str)
                    })
                    contatore += 1
    return tag_scoperti

@app.post("/api/v1/analizzatore-xbrl")
@app.post("/analizzatore-xbrl")
async def upload_xbrl(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        raw_text = file_bytes.decode('utf-8', errors='ignore')
        root = ET.fromstring(raw_text)
        
        # 1. Estrazione Anagrafica Base
        def find_meta(local_name: str, default: str) -> str:
            for elem in root.iter():
                if elem.tag.split('}')[-1] == local_name: return elem.text.strip() if elem.text else default
            return default

        azienda = find_meta("DatiAnagraficiDenominazione", "Azienda non rilevata")
        cf = find_meta("DatiAnagraficiCodiceFiscale", "00000000000")
        
        # 2. Estrazione totale dell'universo dei tag per l'Architetto (Fase 1)
        lista_tutti_tag_file = estrai_universo_tag(root)
        
        # 3. Pre-matching euristico per agevolare l'apertura della pagina
        parificazione_sessione = []
        for p in PARAMETRI_PARIFICAZIONE:
            match_automatico = ""
            esito = "ASSENTE_NEL_FILE"
            
            for t in lista_tutti_tag_file:
                if t["tag_reale"].lower() == p["tag_clean"] and t["contesto"].startswith("c0"):
                    match_automatico = f"it-cc-ci_{t['tag_reale']}"
                    esito = "COERENTE"
                    break
            
            parificazione_sessione.append({
                "id": p["tag_clean"].upper()[:4],
                "macroCategoria": p["categoria"],
                "indiceTarget": p["indice_target"],
                "parametroLogico": p["parametro_logico"],
                "tagMasterCompleto": p["tag_master"],
                "tagClean": p["tag_clean"],
                "tagRilevatoFileXbrl": match_automatico,
                "confrontoEsito": esito
            })

        return {
            "filename": file.filename,
            "azienda": azienda,
            "azienda_codice_fiscale": cf,
            "lista_tutti_tag_file": lista_tutti_tag_file,
            "parificazione_sessione": parificazione_sessione,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore critico workbench: {str(e)}")
