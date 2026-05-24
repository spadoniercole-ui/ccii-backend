import time
from sqlalchemy import func
from models import Configurazione, ProfiloModulo

class ServiceLayer:
    def __init__(self, session):
        self.session = session

    def salva_con_retry(self, profilo_id, azienda_id, spazio_id):
        # 1. Recupero la configurazione dinamica per il numero di tentativi
        config = self.session.query(Configurazione).filter(
            Configurazione.chiave == "max_retry"
        ).first()
        
        # Se non esiste, default a 3 tentativi
        max_retries = int(config.valore) if config else 3

        # 2. Loop di retry (Atomicità garantita dal rollback in caso di errore)
        for attempt in range(max_retries):
            try:
                # Cerco il record attivo per questo profilo
                attivo = self.session.query(ProfiloModulo).filter(
                    ProfiloModulo.profilo_id == profilo_id,
                    ProfiloModulo.data_fine == None
                ).first()
                
                # Chiudo il vecchio record
                if attivo:
                    attivo.data_fine = func.now()
                    attivo.is_old = 1
                
                # Creo il nuovo record
                nuovo = ProfiloModulo(profilo_id=profilo_id)
                self.session.add(nuovo)
                
                # Commit atomico
                self.session.commit()
                return True
                
            except Exception:
                # In caso di conflitto (es. collisione di chiavi), annullo e riprovo
                self.session.rollback()
                time.sleep(0.1) # Breve attesa (100ms)
        
        raise Exception("Errore: superato il limite di tentativi di salvataggio.")
