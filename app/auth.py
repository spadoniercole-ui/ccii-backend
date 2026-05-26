# app/auth.py
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from sqlalchemy.orm import Session

# Importazioni assolute e dirette dalla radice globale
from utils import get_password_hash, verify_password 
from database import get_db
from models import User

# Configurazione JWT
SECRET_KEY = "CAMBIA_QUESTA_CHIAVE_SEGRETISSIMA_IN_PRODUZIONE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def old_bcrypt_verify(plain_password: str, hashed_password_db: str) -> bool:
    """Verifica il vecchio hash bcrypt"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_db.encode('utf-8'))

def update_user_password_in_db(user_id: int, new_hash: str, db: Session) -> None:
    """Aggiorna la password dell'utente nel database dopo la migrazione ad Argon2"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.password = new_hash
        db.commit()

def check_and_migrate(user_id: int, plain_password: str, hashed_password_db: str, db: Session) -> bool:
    """
    Verifica la password. 
    Se è un vecchio bcrypt, la verifica, migra in Argon2 e aggiorna il DB.
    """
    if hashed_password_db.startswith('$2b$') or hashed_password_db.startswith('$2a$'):
        if old_bcrypt_verify(plain_password, hashed_password_db):
            new_hash = get_password_hash(plain_password)
            update_user_password_in_db(user_id, new_hash, db)
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
