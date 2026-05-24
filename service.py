import time
from sqlalchemy import case
from .models import Configurazione, ProfiloModulo

class ServiceLayer:
    def __init__(self, session):
        self.session = session

    def get_config(self, chiave, azienda_id, spazio_id):
        # Recupera il valore più specifico per gerarchia
        config = self.session.query(Configurazione).filter(
            Configurazione.chiave == chiave,
            ((Configurazione.scope_type == 'azienda') & (Configurazione.scope_id == azienda_id) |
             (Configurazione.scope_type == 'spazio') & (Configurazione.scope_id == spazio_id) |
             (Configurazione.scope_type == 'sistema'))
        ).order_by(
            case((Configurazione.scope_type == 'azienda', 1),
                 (Configurazione.scope_type == 'spazio', 2),
                 else_=3)
        ).first()
        return int(config.valore) if config else 3 # Default 3 tentativi

    def salva_con_retry(self, profilo_id, modulo_id, dati_nuovi, azienda_id, spazio_id):
        max_retries = self.get_config("max_retry", azienda_id, spazio_id)
        
        for attempt in range(max_retries):
            try:
                # 1. Trova il max codice per mantenere il salto di 10
                last_record = self.session.query(ProfiloModulo).order_by(ProfiloModulo.id.desc()).first()
                nuovo_codice = (last_record.id // 10 + 1) * 10
                
                # 2. Logica di chiusura e creazione (come discusso)
                # ... (Logica di archiviazione vecchio record e insert)
                
                self.session.commit()
                return True # Successo
            except Exception as e:
                self.session.rollback()
                time.sleep(0.1) # Attesa breve prima del retry
        
        raise Exception("Impossibile completare il salvataggio: numero massimo di tentativi raggiunto.")
