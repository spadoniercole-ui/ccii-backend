import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Recuperiamo l'URL del database dalle variabili d'ambiente (tipico su Railway)
# Se non esiste, usa SQLite in locale come fallback per non bloccarsi
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# 2. Creiamo il motore di connessione
# 'connect_args' serve solo se usiamo SQLite in locale
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# 3. Creiamo la fabbrica di sessioni
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Definiamo la Base per i modelli
Base = declarative_base()

# 5. Funzione di dipendenza per FastAPI (get_db)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
