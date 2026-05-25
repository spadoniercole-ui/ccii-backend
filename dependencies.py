from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models

# 1. Recupera l'utente corrente (assumiamo di avere un sistema di token, 
# per ora semplifichiamo la logica di controllo)
def get_current_user(token: str, db: Session = Depends(get_db)):
    # Qui andrebbe la logica di decodifica JWT. 
    # Per ora, usiamo una logica simulata che puoi sostituire col tuo sistema di autenticazione.
    user = db.query(models.User).filter(models.User.email == token).first() # Semplificazione
    if not user:
        raise HTTPException(status_code=401, detail="Non autenticato")
    return user

# 2. Il "Gatekeeper" per il Super Admin
def require_superadmin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Accesso negato: solo i Super Admin possono accedere a questa rotta."
        )
    return current_user
