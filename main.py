from database import SessionLocal, engine, Base
from services import ServiceLayer

# Inizializzazione DB
Base.metadata.create_all(bind=engine)

def main():
    db = SessionLocal()
    try:
        service = ServiceLayer(db)
        # Esempio: esecuzione della logica di salvataggio
        service.salva_con_retry(profilo_id=1, azienda_id=1, spazio_id=1)
        print("Salvataggio completato correttamente.")
    except Exception as e:
        print(f"Errore critico: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
