# auth.py
import sys
import os

# Forza Python a includere la radice del progetto nei percorsi di ricerca
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from utils import get_password_hash, verify_password 

# Importazioni assolute garantite dal fix del sys.path sopra
from database import get_db
from models import User
from db.crud import update_user_password_in_db  # Riconosciuto correttamente nella radice

# Configurazione JWT
SECRET_KEY = "CAMBIA_QUESTA_CHIAVE_SEGRETISSIMA_IN_PRODUZIONE" # Usa una variabile d'ambiente!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def old_bcrypt_verify(plain_password: str, hashed_password_db: str) -> bool:
    """Verifica il vecchio hash bcrypt"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_db.encode('utf-8'))

def check_and_migrate(user_id: int, plain_password: str, hashed_password_db: str) -> bool:
    """
    Verifica la password. 
    Se è un vecchio bcrypt, la verifica, migra in Argon2 e aggiorna il DB.
    Se è già Argon2, la verifica semplicemente.
    Ritorna True se la password è corretta, False altrimenti.
    """
    if hashed_password_db.startswith('$2b$') or hashed_password_db.startswith('$2a$'):
        if old_bcrypt_verify(plain_password, hashed_password_db):
            new_hash = get_password_hash(plain_password)
            update_user_password_in_db(user_id, new_hash)
            return True 
        return False 
    
    return verify_password(plain_password, hashed_password_db)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
