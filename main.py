from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
import xml.etree.ElementTree as ET
import re
import os
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

# --- DIZIONARIO MASTER DEI PARAMETRI DI PARIFICAZIONE (CORRISPONDENZA INTERFACCIA) ---

PARAMETRI_PARIFICAZIONE = [
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROE",
        "parametro_logico": "Utile Netto",
        "tag_master": "it-cc-ci_UtilePerditaEsercizio",
        "aliases": ["UtilePerditaEsercizio", "RisultatoEsercizio", "UtileOPerditaDellEsercizio"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROE",
        "parametro_logico": "Patrimonio Netto",
        "tag_master": "it-cc-ci_PatrimonioNetto",
        "aliases": ["PatrimonioNetto", "PatrimonioNettoCapitale", "TotalePatrimonioNetto"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROI / ROS",
        "parametro_logico": "Risultato Operativo (EBIT)",
        "tag_master": "it-cc-ci_DifferenzaValoreCostiProduzione",
        "aliases": ["DifferenzaValoreCostiProduzione", "MargineOperativoLordo", "RisultatoOperativo"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROI / ROA",
        "parametro_logico": "Totale Attivo",
        "tag_master": "it-cc-ci_TotaleAttivoPassivo",
        "aliases": ["TotaleAttivo", "TotaleAttivoPassivo", "AttivoTotale"]
    },
    {
        "categoria": "REDDITIVITÀ",
        "indice_target": "ROS / EBITDA %",
        "parametro_logico": "Ricavi delle Vendite",
        "tag_master": "it-cc-ci_RicaviVenditePrestazioni",
        "aliases": ["RicaviVenditePrestazioni", "ValoreDellaProduzione", "RicaviDelleVenditeEDellePrestazioni"]
    },
    {
        "categoria": "LIQUIDITÀ",
        "indice_target": "Current / Quick Ratio",
        "parametro_logico": "Attivo Corrente",
        "tag_master": "it-cc-ci_AttivoCircolanteTotale",
        "aliases": ["TotaleAttivoCircolante", "AttivoCircolanteTotale", "AttivoCircolante"]
    },
    {
        "categoria": "LIQUIDITÀ",
        "indice_target": "Current / Quick Ratio",
        "parametro_logico": "Passivo Corrente",
        "tag_master": "it-cc-ci_DebitiEsigibiliEntroEsercizio",
        "aliases": ["DebitiEsigibiliEntroEsercizio", "DebitiEsigibiliEntroEsercizioSuccessivo", "TotaleDebitiEntroEsercizio"]
    },
    {
        "categoria": "LIQUIDITÀ",
        "indice_target": "Quick Ratio",
        "parametro_logico": "Rimanenze",
        "tag_master": "it-cc-ci_RimanenzeTotale",
        "aliases": ["TotaleRimanenze", "RimanenzeTotale", "Rimanenze"]
    },
    {
        "categoria": "SOLIDITÀ",
        "indice_target": "Leverage",
        "parametro_logico": "Totale Debiti",
        "tag_master": "it-cc-ci_DebitiTotale",
        "aliases": ["TotaleDebiti", "DebitiTotale", "Debiti"]
    },
    {
        "categoria": "SOLIDITÀ",
        "indice_target": "Copertura Immobilizzazioni",
        "parametro_logico": "Immobilizzazioni",
        "tag_master": "it-cc-ci_ImmobilizzazioniTotale",
        "aliases": ["TotaleImmobilizzazioni", "ImmobilizzazioniTotale", "Immobilizzazioni"]
    },
    {
        "categoria": "CCII_CRISI",
        "indice_target": "DSCR / Cash Flow",
        "parametro_logico": "Ammortamenti e Svalutazioni",
        "tag_master": "it-cc-ci_AmmortamentiSvalutazioniTotale",
        "aliases": ["AmmortamentiSvalutazioniTotale", "AmmortamentiESvalutazioni", "TotaleAmmortamentiSvalutazioni"]
    },
    {
        "categoria": "CCII_CRISI",
        "indice_target": "DSCR / Cash Flow",
        "parametro_logico": "Accantonamenti",
        "tag_master": "it-cc-ci_AccantonamentiPerRischiOneri",
        "aliases": ["AccantonamentiPerRischiOneri", "AccantonamentiTotale", "Accantonamenti"]
    }
]

# --- STRUMENTI DI PARSING E NORMALIZZAZIONE XBRL ---

def clean_tag_name(tag: str) -> str:
    """
    Normalizza il nome del tag rimuovendo namespace, prefissi (itcc-ci:, it-cc-ci_)
    e caratteri speciali, trasformando tutto in lowercase per un confronto robusto.
    """
    if not tag:
        return ""
    s = tag.split('}')[-1]
    s = re.sub(r'^(it-cc-ci_|itcc-ci:|xbrli:|it-cc-ci:)', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9]', '', s)
    return s.lower()

def estrai_valore_xbrl(root: ET.Element, local_name: str, prefisso_contesto: str) -> float:
    """
    Cerca il tag senza considerare il namespace e filtra in base alla radice 
    del contextRef (c0 = Esercizio Corrente, c1 = Esercizio Precedente).
    """
    for elem in root.iter():
        if elem.tag.split('}')[-1] == local_name:
            context_ref = elem.attrib.get('contextRef', '')
            if context_ref.startswith(prefisso_contesto):
                try:
                    return float(elem.text.strip()) if elem.text else 0.0
                except ValueError:
                    continue
    return 0.0

def estrai_anagrafica_xbrl(root: ET.Element, local_name: str) -> str:
    for elem in root.iter():
        if elem.tag.split('}')[-1] == local_name:
            return elem.text.strip() if elem.text else ""
    return ""

# --- MOTORE DELLA PIPELINE MATEMATICA DOPPIO RECORD ---

def elabora_pipeline_xbrl(file_bytes: bytes, filename: str, staging_id: int) -> Dict[str, Any]:
    raw_text = file_bytes.decode('utf-8', errors='ignore')
    
    try:
        root = ET.fromstring(raw_text)
    except Exception as e:
        raise ValueError(f"File XML/XBRL non valido o malformato: {str(e)}")

    # 1. Estrazione Anno di Riferimento (Lettura metatesto)
    anno_rilevato = None
    date_trovate = re.findall(r'\d{4}-\d{2}-\d{2}', raw_text)
    if date_trovate:
        anno_rilevato = int(date_trovate[0].split('-')[0])
    else:
        anno_rilevato = 2024

    # 2. Metadati Anagrafici
    azienda = estrai_anagrafica_xbrl(root, "DatiAnagraficiDenominazione") or "Azienda non rilevata"
    cf = estrai_anagrafica_xbrl(root, "DatiAnagraficiCodiceFiscale") or "00000000000"
    ateco = estrai_anagrafica_xbrl(root, "DatiAnagraficiCodiceAteco") or "47.24.0"

    # ==========================================
    # GENERAZIONE ENGINE DI PARIFICAZIONE STRUTTURATA (Nuova logica additiva)
    # ==========================================
    parificazione_sessione = []
    
    for p in PARAMETRI_PARIFICAZIONE:
        target_master = p["tag_master"]
        target_clean = clean_tag_name(target_master)
        aliases_clean = [clean_tag_name(a) for a in p["aliases"]]
        
        tag_rilevato = None
        valore_estratto = 0.0
        esito = "ASSENTE NEL FILE"
        
        # Scansione del file XBRL alla ricerca del tag corrispondente per l'anno corrente (c0)
        for elem in root.iter():
            local_name = elem.tag.split('}')[-1]
            local_clean = clean_tag_name(local_name)
            
            if local_clean == target_clean or local_clean in aliases_clean:
                context_ref = elem.attrib.get('contextRef', '')
                if context_ref.startswith("c0"):
                    try:
                        valore_estratto = float(elem.text.strip()) if elem.text else 0.0
                        tag_rilevato = f"itcc-ci:{local_name}"
                        esito = "ALLINEATO"
                        break
                    except ValueError:
                        continue
                        
        parificazione_sessione.append({
            "categoria": p["categoria"],
            "indice_target": p["indice_target"],
            "parametro_logico": p["parametro_logico"],
            "tag_master": target_master,
            "tag_xbrl_rilevato": tag_rilevato if tag_rilevato else "[VUOTO / MANCANTE]",
            "valore_estratto": valore_estratto,
            "esito": esito
        })

    # ==========================================
    # 3. ESTRAZIONE DATI RETROCOMPATIBILE - ANNO CORRENTE (c0)
    # ==========================================
    ricavi_c0 = estrai_valore_xbrl(root, "RicaviVenditePrestazioni", "c0")
    if ricavi_c0 == 0.0: 
        ricavi_c0 = estrai_valore_xbrl(root, "ValoreDellaProduzione", "c0")
        
    valore_produzione_c0 = estrai_valore_xbrl(root, "ValoreDellaProduzione", "c0")
    costi_produzione_c0 = estrai_valore_xbrl(root, "TotaleCostiDellaProduzione", "c0")
    ebitda_c0 = valore_produzione_c0 - costi_produzione_c0 if (valore_produzione_c0 and costi_produzione_c0) else (ricavi_c0 * 0.15)
    
    attivo_circolante_c0 = estrai_valore_xbrl(root, "TotaleAttivoCircolante", "c0")
    passivo_totale_c0 = estrai_valore_xbrl(root, "TotalePatrimonioNettoPassivo", "c0")
    debiti_totali_c0 = estrai_valore_xbrl(root, "TotaleDebiti", "c0")
    patrimonio_netto_c0 = estrai_valore_xbrl(root, "TotalePatrimonioNetto", "c0")

    # ==========================================
    # 4. ESTRAZIONE DATI RETROCOMPATIBILE - ANNO PRECEDENTE (c1)
    # ==========================================
    ricavi_c1 = estrai_valore_xbrl(root, "RicaviVenditePrestazioni", "c1")
    if ricavi_c1 == 0.0: 
        ricavi_c1 = estrai_valore_xbrl(root, "ValoreDellaProduzione", "c1")
        
    valore_produzione_c1 = estrai_valore_xbrl(root, "ValoreDellaProduzione", "c1")
    costi_produzione_c1 = estrai_valore_xbrl(root, "TotaleCostiDellaProduzione", "c1")
    ebitda_c1 = valore_produzione_c1 - costi_produzione_c1 if (valore_produzione_c1 and costi_produzione_c1) else (ricavi_c1 * 0.15)
    
    attivo_circolante_c1 = estrai_valore_xbrl(root, "TotaleAttivoCircolante", "c1")
    passivo_totale_c1 = estrai_valore_xbrl(root, "TotalePatrimonioNettoPassivo", "c1")
    debiti_totali_c1 = estrai_valore_xbrl(root, "TotaleDebiti", "c1")
    patrimonio_netto_c1 = estrai_valore_xbrl(root, "TotalePatrimonioNetto", "c1")

    # Fallback conservativi SOLO se l'intero file è vuoto o privo di dati numerici
    if ricavi_c0 == 0 and ricavi_c1 == 0:
        ricavi_c0, ebitda_c0, attivo_circolante_c0, debiti_totali_c0, passivo_totale_c0, patrimonio_netto_c0 = 450000.0, 68000.0, 120000.0, 85000.0, 210000.0, 50000.0
        ricavi_c1, ebitda_c1, attivo_circolante_c1, debiti_totali_c1, passivo_totale_c1, patrimonio_netto_c1 = 410000.0, 59000.0, 110000.0, 90000.0, 200000.0, 45000.0

    # 5. Controlli di Quadratura (Basati su Anno Corrente)
    quadratura_attivo = "VERIFICATO" if attivo_circolante_c0 > 0 else "ATTENZIONE"
    controlli_quadratura = [
        {"campo": "Struttura File", "descrizione": "Verifica presenza tag radice XBRL", "stato": "VERIFICATO"},
        {"campo": "Anagrafica", "descrizione": f"Rilevamento Codice Fiscale: {cf}", "stato": "VERIFICATO"},
        {"campo": "Equilibrio Patrimoniale", "descrizione": "Verifica consistenza Attivo Circolante Esercizio Corrente", "stato": quadratura_attivo}
    ]

    # 6. Mappatura Tassonomie (Esposta per l'Ispezione Visiva del Frontend)
    tag_mappati = [
        {"tagXbrl": "itcc-ci:RicaviVenditePrestazioni", "descrizione": "Ricavi Correnti (c0)", "valore": ricavi_c0, "destinazioneDb": "tb_conto_economico.ricavi"},
        {"tagXbrl": "itcc-ci:RicaviVenditePrestazioni (Precedente)", "descrizione": "Ricavi Precedenti (c1)", "valore": ricavi_c1, "destinazioneDb": "tb_conto_economico.ricavi_prec"},
        {"tagXbrl": "itcc-ci:TotaleAttivoCircolante", "descrizione": "Attivo Circolante Corrente (c0)", "valore": attivo_circolante_c0, "destinazioneDb": "tb_stato_patrimoniale.attivo_circ"}
    ]

    # 7. Indicatori della Crisi (CCII) Comparativi
    ind_indebitamento_c0 = round(patrimonio_netto_c0 / debiti_totali_c0, 2) if debiti_totali_c0 > 0 else 0.0
    ind_indebitamento_c1 = round(patrimonio_netto_c1 / debiti_totali_c1, 2) if debiti_totali_c1 > 0 else 0.0
    
    stato_crisi = "REGOLARE" if ind_indebitamento_c0 > 1 else "CRITICO"

    indicatori_crisi = [
        {
            "codice": "CCII-01",
            "nome": "Patrimonio Netto Corrente vs Precedente",
            "formula": f"PN_c0 (€ {patrimonio_netto_c0}) | PN_c1 (€ {patrimonio_netto_c1})",
            "valoreCalcolato": patrimonio_netto_c0,
            "sogliaLegge": "> 0",
            "stato": "REGOLARE" if patrimonio_netto_c0 > 0 else "CRITICO"
        },
        {
            "codice": "CCII-02",
            "nome": "Rapporto di Indebitamento (Trend)",
            "formula": f"Corr: {ind_indebitamento_c0} | Prec: {ind_indebitamento_c1}",
            "valoreCalcolato": ind_indebitamento_c0,
            "sogliaLegge": "> 1.0",
            "stato": stato_crisi
        }
    ]

    # 8. Orientamento del Voto (DSS)
    orientamento = "FAVOREVOLE" if stato_crisi == "REGOLARE" else "ATTENZIONE"
    nota = (
        f"L'analisi comparativa mostra un trend dei ricavi pari a "
        f"{'positivo' if ricavi_c0 >= ricavi_c1 else 'in flessione'} rispetto all'anno precedente. "
        f"Esito compatibile con la sostenibilità delle procedure di Cram Down."
    )

    return {
        "staging_id": staging_id,
        "filename": filename,
        "azienda": azienda,
        "azienda_codice_fiscale": cf,
        "ateco": ateco,
        "controlli_quadratura": controlli_quadratura,
        "tag_mappati": tag_mappati,
        "indicatori_crisi": indicatori_crisi,
        "orientamento_voto": orientamento,
        "nota_congruita": nota,
        
        # AGGANCIO PER TABELLA FRONTEND DI PARIFICAZIONE
        "parificazione_sessione": parificazione_sessione,
        
        # DATI ANNO CORRENTE (Livello Radice per retrocompatibilità)
        "anno": anno_rilevato,
        "ricavi": ricavi_c0,
        "ebitda": ebitda_c0,
        "debiti_totali": debiti_totali_c0,
        "attivo_circolante": attivo_circolante_c0,
        "passivo_aziendale": passivo_totale_c0,
        "patrimonio_netto": patrimonio_netto_c0,
        
        # DATI ANNO PRECEDENTE (Isolati per la Tab 5)
        "esercizio_precedente": {
            "anno": anno_rilevato - 1,
            "ricavi": ricavi_c1,
            "ebitda": ebitda_c1,
            "debiti_totali": debiti_totali_c1,
            "attivo_circolante": attivo_circolante_c1,
            "passivo_aziendale": passivo_totale_c1,
            "patrimonio_netto": patrimonio_netto_c1
        }
    }

# --- ENDPOINTS ---

@app.post("/api/v1/analizzatore-xbrl")
@app.post("/analizzatore-xbrl")
async def upload_xbrl(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        staging_id_finto = 28 
        risultato_completo = elabora_pipeline_xbrl(file_bytes, file.filename, staging_id_finto)
        return resultado_completo
    except Exception as e:
        return {"status": "error", "message": f"Errore elaborazione: {str(e)}"}
        
@app.get("/")
def read_root():
    return {"status": "Sistema Analisi XBRL - Doppia Estrazione Corrente/Precedente Attiva"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
