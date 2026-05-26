from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importazioni assolute corrette: i file sono nella stessa cartella
from database import get_db
import models

def get_current_user(db: Session = Depends(get_db)):
    # Placeholder temporaneo in attesa dell'integrazione JWT
    raise HTTPException(status_code=401, detail="Autenticazione mancante (implementa JWT)")

def require_superadmin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Accesso negato: solo i Super Admin possono accedere a questa rotta."
        )
    return current_user
