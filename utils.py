# crud.py
from sqlalchemy.orm import Session
from models import User
from utils import get_password_hash

def create_user(db: Session, email: str, password: str, role: str = "user", is_superuser: bool = False):
    hashed_pw = get_password_hash(password)
    db_user = User(
        email=email, 
        hashed_password=hashed_pw, 
        role=role, 
        is_superuser=is_superuser
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
