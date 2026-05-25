import os
from sqlalchemy import create_engine, text

# Carica l'URL dalla variabile d'ambiente (quella che imposterai su Railway)
# Per testare in locale, puoi sostituirla temporaneamente con la stringa reale
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Connessione al database riuscita! ✅")
        print(f"Risultato: {result.scalar()}")
except Exception as e:
    print("Errore di connessione al database ❌")
    print(f"Dettaglio: {e}")
