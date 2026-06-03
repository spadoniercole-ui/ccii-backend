import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Recupera solo il NOME della variabile d'ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Se la variabile non è trovata, gestisci l'errore per evitare crash silenziosi
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("La variabile d'ambiente DATABASE_URL non è impostata!")

# 3. Correggi il prefisso se necessario (come facevi già nel tuo codice)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
