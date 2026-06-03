import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Recupera il NOME della variabile, non il valore
# Assicurati che su Railway la variabile si chiami esattamente DATABASE_URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Controllo di sicurezza
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("La variabile d'ambiente DATABASE_URL non è impostata!")

# 3. Correzione del prefisso (come facevi già)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
