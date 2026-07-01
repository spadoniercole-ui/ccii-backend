from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
import xml.etree.ElementTree as ET
import re
import os
from typing import Dict, Any, List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MAPPA MASTER DEI PARAMETRI RICHIESTI DAGLI INDICI DELLA CRISI ---
PARAMETRI_PARIFICAZIONE = [
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROE",
        "parametro_logico": "Utile Netto",
        "tag_master": "UtilePerditaEsercizio",
        "aliases": ["UtilePerditaEsercizio", "RisultatoEsercizio", "UtileOPerditaDellEsercizio"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROE",
        "parametro_logico": "Patrimonio Netto",
        "tag_master": "TotalePatrimonioNetto",
        "aliases": ["PatrimonioNetto", "PatrimonioNettoCapitale", "TotalePatrimonioNetto"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROI / ROS",
        "parametro_logico": "Risultato Operativo (EBIT)",
        "tag_master": "DifferenzaValoreCostiProduzione",
        "aliases": ["DifferenzaValoreCostiProduzione", "MargineOperativoLordo", "RisultatoOperativo"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROS / EBITDA %",
        "parametro_logico": "Ricavi delle Vendite",
        "tag_master": "RicaviVenditePrestazioni",
        "aliases": ["RicaviVenditePrestazioni", "ValoreDellaProduzione"]
    },
    {
        "categoria": "LIQUIDITÀ",
        "indice_target": "Current Ratio",
        "parametro_logico": "Attivo Corrente",
        "tag_master": "TotaleAttivoCircolante",
        "aliases": ["TotaleAttivoCircolante", "AttivoCircolanteTotale"]
    },
    {
        "categoria": "LIQUIDITÀ",
        "indice_target": "Current Ratio",
        "parametro_logico": "Passivo Corrente",
        "tag_master": "DebitiEsigibiliEntroEsercizio",
        "aliases": ["DebitiEsigibiliEntroEsercizio", "TotaleDebitiEntroEsercizio"]
    },
    {
        "categoria": "SOLIDITÀ",
        "indice_target": "Leverage",
        "parametro_logico": "Totale Debiti",
        "tag_master": "TotaleDebiti",
        "aliases": ["TotaleDebiti", "DebitiTotale"]
    }
]

def clean_tag_name(tag: str) -> str:
    if not tag: return ""
    s = tag.split('}')[-1]
    s = re.sub(r'^(it-cc-ci_|itcc-ci:|xbrli:|it-cc-ci:)', '', s, flags=re.IGNORECASE)
    return s.strip()

def estrai_anagrafica_xbrl(root: ET.Element, local_name: str) -> str:
    for elem in root.iter():
        if elem.tag.split('}')[-1] == local_name:
            return elem.text.strip() if elem.text else ""
    return ""

def elabora_pipeline_xbrl(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    raw_text = file_bytes.decode('utf-8', errors='ignore')
    try:
        root = ET.fromstring(raw_text)
    except Exception as e:
        raise ValueError(f"XML/XBRL malformato: {str(e)}")

    # Metadati Aziendali
    azienda = estrai_anagrafica_xbrl(root, "DatiAnagraficiDenominazione") or "Azienda Rilevata"
    cf = estrai_anagrafica_xbrl(root, "DatiAnagraficiCodiceFiscale") or "00000000000"
    
    # 1. ESTRAZIONE FLAT INTEGRALE DI TUTTI I TAG NUMERICI
    mappa_tag_file = []
    contatore = 1
    
    for elem in root.iter():
        local_name = clean_tag_name(elem.tag)
        context_ref = elem.attrib.get('contextRef', '')
        
        if context_ref and elem.text and elem.text.strip():
            try:
                valore_float = float(elem.text.strip())
                periodo = "Corrente (c0)" if "c0" in context_ref.lower() else "Precedente (c1)" if "c1" in context_ref.lower() else "Altro"
                
                mappa_tag_file.append({
                    "id_veloce": f"T{contatore}",
                    "tag_reale": local_name,
                    "contesto": context_ref,
                    "periodo": periodo,
                    "valore": valore_float
                })
                contatore += 1
            except ValueError:
                continue

    # 2. MATCHING DETERMINISTICO PER VALORI STANDARD
    parificazione_sessione = []
    for p in PARAMETRI_PARIFICAZIONE:
        valore_c0 = 0.0
        valore_c1 = 0.0
        tag_agganciato = "[NON RILEVATO]"
        
        # Cerca corrispondenze nell'universo flat appena generato
        for t in mappa_tag_file:
            if t["tag_reale"].lower() == p["tag_master"].lower() or t["tag_reale"] in p["aliases"]:
                if "c0" in t["contesto"].lower():
                    valore_c0 = t["valore"]
                    tag_agganciato = t["tag_reale"]
                elif "c1" in t["contesto"].lower():
                    valore_c1 = t["valore"]

        parificazione_sessione.append({
            "categoria": p["categoria"],
            "indice_target": p["indice_target"],
            "parametro_logico": p["parametro_logico"],
            "tag_master": p["tag_master"],
            "tag_xbrl_rilevato": tag_agganciato,
            "valore_corrente": valore_c0,
            "valore_precedente": valore_c1,
            "esito": "ALLINEATO" if tag_agganciato != "[NON RILEVATO]" else "ASSENTE"
        })

    return {
        "status": "success",
        "filename": filename,
        "azienda": azienda,
        "azienda_codice_fiscale": cf,
        "mappa_tag_file": mappa_tag_file,
        "parificazione_sessione": parificazione_sessione
    }

@app.post("/api/v1/analizzatore-xbrl")
async def upload_xbrl(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        return elabora_pipeline_xbrl(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
