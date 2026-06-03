import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Railway fornisce la stringa completa in DATABASE_URL
SQLALCHEMY_DATABASE_URL = os.getenv("postgresql://postgres:qBOGUzEOJvncBDqempQDLQcrhuLCXCLe@postgres.railway.internal:5432/railwaypostgresql://postgres:qBOGUzEOJvncBDqempQDLQcrhuLCXCLe@postgres.railway.internal:5432/railway")

# Se DATABASE_URL inizia con 'postgres://', SQLAlchemy potrebbe richiedere 'postgresql://'
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
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
