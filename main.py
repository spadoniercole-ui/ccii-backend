from fastapi import FastAPI, Depends # 👈 Modifica: Aggiunto Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import Spazio

# Creazione tabelle (da mantenere se necessario all'avvio)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione CORS
origins = [
    "https://cciiplatform.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def home():
    return {"status": "running", "message": "API Spazi funzionante correttamente"}

@app.get("/spazi/{spazio_id}")
def leggi_spazio(spazio_id: int, db: Session = Depends(get_db)):
    # Corretto: usiamo spazio_id per filtrare 🔍
    spazio = db.query(Spazio).filter(Spazio.id == spazio_id).first()
    
    if spazio is None:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
        
    return {
        "id": spazio.id,
        "licenza_id": spazio.licenza_id,
        "nome_spazio": spazio.nome_spazio,
        "tipologia": spazio.tipologia
    }
