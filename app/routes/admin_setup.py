import sys
import os

# Sale di due livelli (da app/routes/ a app/ e poi a backend/) per registrare la radice
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Importazioni assolute e pulite
from database import get_db 
from models import User
from services.admin_service import admin_service 

router = APIRouter(prefix="/admin-setup", tags=[\"admin-setup\"])

class SpaceCreateRequest(BaseModel):
    nome: str
    licenza_id: int
    tipo_spazio_id: int

@router.get(\"/status\")
def check_setup_status(db: Session = Depends(get_db)):\n    return {\"initialized\": admin_service.is_initialized(db)}

@router.post(\"/create-space\")
def create_space(data: SpaceCreateRequest, db: Session = Depends(get_db)):
    try:
        spazio = admin_service.validate_license_and_create_space(
            db, 
            data.nome, 
            data.licenza_id, 
            data.tipo_spazio_id
        )
        return {\"message\": \"Spazio creato\", \"id\": spazio.id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
