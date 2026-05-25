import os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# 1. Recupera l'URL dall'ambiente. 
# Se non la trova, il programma si ferma subito (fail-fast)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL non trovata nelle variabili d'ambiente. Impostala su Railway.")

# 2. Configurazione engine con SSL
# Aggiungiamo 'sslmode': 'require' perché Railway lo richiede per le connessioni esterne
connect_args = {"sslmode": "require"}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)

# 3. Setup sessione e base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 4. Dependency per FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
