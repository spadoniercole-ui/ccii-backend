from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
# Assumo tu abbia una funzione per verificare lo stato nel DB
from database import get_db 
from services.admin_service import admin_service

router = APIRouter(prefix="/admin-setup", tags=["admin-setup"])

class SetupRequest(BaseModel):
    username: str
    password: str
    email: str

@router.get("/status")
def check_setup_status():
    """Controlla se il sistema è già stato inizializzato."""
    # Logica pragmatica: torna booleano
    is_setup = admin_service.is_initialized() 
    return {"initialized": is_setup}

@router.post("/initialize")
def initialize_system(data: SetupRequest):
    """Esegue il setup iniziale."""
    if admin_service.is_initialized():
        raise HTTPException(status_code=400, detail="Il sistema è già configurato.")
    
    try:
        admin_service.create_admin(data)
        return {"message": "Setup completato con successo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
