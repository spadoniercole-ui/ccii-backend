import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Recupera il valore reale dalla variabile d'ambiente definita su Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Se non è impostata, usa un valore di default per il debug locale
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:qBOGUzEOJvncBDqempQDLQcrhuLCXCLe@postgres.railway.internal:5432/railway"

# 3. Correzione protocollo per SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
