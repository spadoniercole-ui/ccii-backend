# auth.py
from utils import get_password_hash, verify_password # Argon2
import bcrypt # Importa direttamente bcrypt per verificare i vecchi hash
from db.crud import update_user_password_in_db # Importa la tua funzione di DB

def old_bcrypt_verify(plain_password: str, hashed_password_db: str) -> bool:
    """Verifica il vecchio hash bcrypt senza passare per passlib"""
    # bcrypt.checkpw accetta byte, convertiamo le stringhe
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_db.encode('utf-8'))

def check_and_migrate(user_id: int, plain_password: str, hashed_password_db: str):
    # 1. Se sembra un hash bcrypt (vecchio)
    if hashed_password_db.startswith('$2b$') or hashed_password_db.startswith('$2a$'):
        if old_bcrypt_verify(plain_password, hashed_password_db):
            # Aggiorna il DB con il nuovo hash Argon2
            new_hash = get_password_hash(plain_password)
            update_user_password_in_db(user_id, new_hash)
            return True # Login riuscito
        return False # Password errata
    
    # 2. Se è già Argon2 (o un formato moderno)
    return verify_password(plain_password, hashed_password_db)
