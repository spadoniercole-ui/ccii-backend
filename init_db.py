# init_db.py
from database import SessionLocal
from crud import create_user
from models import User

def init_system():
    db = SessionLocal()
    
    # 1. Controllo esistenza Super Admin
    admin = db.query(User).filter(User.is_superuser == True).first()
    
    if not admin:
        print("Super Admin non trovato. Creazione in corso...")
        create_user(
            db, 
            email="admin@tuodominio.com", 
            password="una_password_molto_sicura", 
            role="admin", 
            is_superuser=True
        )
        print("Super Admin creato con successo.")
    else:
        print(f"Super Admin già esistente: {admin.email}")
    
    db.close()

if __name__ == "__main__":
    init_system()
