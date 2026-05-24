import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Recuperiamo l'URL e gestiamo stringhe vuote o formati legacy (postgres://)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Se la variabile è vuota o assente, usa SQLite locale
    DATABASE_URL = "ghcr.io/railwayapp-templates/postgres-ssl:18"
elif DATABASE_URL.startswith("postgres://"):
    # Railway spesso usa "postgres://", ma SQLAlchemy vuole "postgresql://"
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 2. Creiamo il motore di connessione con gli argomenti corretti
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
