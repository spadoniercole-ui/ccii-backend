import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Recupera l'URL dalla variabile d'ambiente impostata su Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# Se DATABASE_URL non è impostato, il backend fallirà correttamente 
# (invece di crashare per errore di sintassi durante l'import)
if not DATABASE_URL:
    raise ValueError("La variabile d'ambiente DATABASE_URL non è definita!")

# Correzione del prefisso richiesto da SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,   # Verifica che la connessione sia attiva prima di inviare dati
    pool_recycle=1800     # Rigenera le connessioni ogni 30 minuti per evitare che scadano
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
