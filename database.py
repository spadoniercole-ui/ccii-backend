from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL di connessione al database fornito
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:aQXXZdWkaxudAyYhTGitMsZUQigAhMxi@viaduct.proxy.rlwy.net:48125/railway"

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
