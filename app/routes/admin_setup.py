# app/routes/admin_setup.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Importazioni assolute dirette dalla radice globale
from database import get_db 
from models import User
from admin_service import AdminService # Importazione corretta della classe

router = APIRouter(prefix="/admin-setup", tags=["admin-setup"])
admin_service = AdminService() # Inizializzazione locale dell'istanza se non esportata come oggetto

class SpaceCreateRequest(BaseModel):
    nome: str
    licenza_id: int
    tipo_spazio_id: int

@router.get("/status")
def check_setup_status(db: Session = Depends(get_db)):
    return {"initialized": admin_service.is_initialized(db)}

@router.post("/create-space")
def create_space(data: SpaceCreateRequest, db: Session = Depends(get_db)):
    try:
        spazio = admin_service.validate_license_and_create_space(
            db, 
            data.nome, 
            data.licenza_id, 
            data.tipo_spazio_id
        )
        return {"message": "Spazio creato", "id": spazio.id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
