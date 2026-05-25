from sqlalchemy.orm import Session
from models import Licenza, Spazio
from fastapi import HTTPException
from datetime import date

class AdminService:
    def is_initialized(self, db: Session):
        # Verifica se esiste almeno un superuser o una configurazione base
        # Implementa qui la tua logica esistente
        return False 

    def create_admin(self, db: Session, data):
        # La tua logica esistente
        pass

    def validate_license_and_create_space(self, db: Session, space_name: str, license_id: int, tipo_spazio_id: int):
        # 1. Validazione Licenza
        licenza = db.query(Licenza).filter(Licenza.id == license_id).first()
        if not licenza:
            raise HTTPException(status_code=404, detail="Licenza non trovata")
        
        if licenza.data_scadenza < date.today():
            raise HTTPException(status_code=400, detail="Licenza scaduta")

        # 2. Validazione Limiti (Esempio: max_spazi)
        spazi_esistenti = db.query(Spazio).filter(Spazio.licenza_id == license_id).count()
        if spazi_esistenti >= licenza.max_spazi:
            raise HTTPException(status_code=400, detail="Limite massimo di spazi raggiunto per questa licenza")

        # 3. Creazione Spazio
        nuovo_spazio = Spazio(
            nome=space_name,
            licenza_id=license_id,
            tipo_spazio_id=tipo_spazio_id,
            data_scadenza_licenza=licenza.data_scadenza
        )
        db.add(nuovo_spazio)
        db.commit()
        db.refresh(nuovo_spazio)
        return nuovo_spazio

admin_service = AdminService()
