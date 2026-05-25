# init_db.py
from database import SessionLocal, engine
from models import Base
from crud import create_user

# Assicurati che le tabelle esistano
Base.metadata.create_all(bind=engine)

def init():
    db = SessionLocal()
    # Controlla se esiste già un admin per evitare duplicati
    # (Opzionale, ma caldamente consigliato)
    try:
        admin_email = "admin@tuosito.com"
        # Qui potresti aggiungere un controllo get_user_by_email
        create_user(
            db=db, 
            email=admin_email, 
            password="tua_password_sicura", 
            role="admin", 
            is_superuser=True
        )
        print(f"Super admin creato con email: {admin_email}")
    except Exception as e:
        print(f"Errore: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init()
