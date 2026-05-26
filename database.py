from dotenv import load_dotenv
import os

load_dotenv() # Carica le variabili dal file .env

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Recupera l'URL dall'ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL non trovata nelle variabili d'ambiente.")

# CORREZIONE AUTOMATICA PER RAILWAY: convertiamo postgres:// in postgresql://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 2. Setup Database
connect_args = {}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Questa è la base che useranno tutti i modelli
Base = declarative_base()

# 3. Dependency per FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
