from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Aggiungi 'connect_args' per gestire meglio la negoziazione SSL
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require" 
    }
)
# URL di connessione al database fornito
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:SsiUmLbTiHjrgHxAgiNcjDbXvcLxMCNk@postgres.railway.internal:5432/railway"

# Creazione dell'engine
# echo=True è utile in fase di debug per vedere le query SQL nei log
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal servirà per ogni richiesta API
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base serve per definire i modelli
Base = declarative_base()

# Dependency per usare il database in FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
