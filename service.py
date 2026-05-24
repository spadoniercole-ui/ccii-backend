import time
from sqlalchemy import func
from models import Configurazione, ProfiloModulo

class ServiceLayer:
    def __init__(self, session):
        self.session = session

    def salva_con_retry(self, profilo_id, azienda_id, spazio_id):
        # Recupero configurazione
        config = self.session.query(Configurazione).filter(
            Configurazione.chiave == "max_retry"
        ).first()
        max_retries = int(config.valore) if config else 3

        for attempt in range(max_retries):
            try:
                # Chiusura record attivo
                attivo = self.session.query(ProfiloModulo).filter(
                    ProfiloModulo.profilo_id == profilo_id,
                    ProfiloModulo.data_fine == None
                ).first()
                
                if attivo:
                    attivo.data_fine = func.now()
                    attivo.is_old = 1
                
                # Inserimento nuovo record
                nuovo = ProfiloModulo(profilo_id=profilo_id)
                self.session.add(nuovo)
                self.session.commit()
                return True
            except Exception:
                self.session.rollback()
                time.sleep(0.1)
        raise Exception("Numero massimo tentativi raggiunto.")
