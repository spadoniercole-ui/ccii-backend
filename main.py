from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from database import engine, Base, get_db
from models import Spazio, User, Role

# Genera le tabelle nel database se non esistono
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione CORS per permettere al frontend di comunicare col backend
origins = [
    "https://cciiplatform.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema per i dati in ingresso dal login
class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
def home():
    return {"status": "running", "message": "API funzionante correttamente"}

@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # 1. Verifica esistenza utente
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali errate")
        
    ora = datetime.utcnow()
    alert_messaggi = []

    # 2. Controllo Licenza dello Spazio
    spazio = db.query(Spazio).filter(Spazio.id == user.id).first() 
    
    if spazio and spazio.data_scadenza_licenza:
        giorni_licenza = (spazio.data_scadenza_licenza - ora).days
        
        if giorni_licenza <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Accesso bloccato: Licenza scaduta. Contattare il reparto commerciale."
            )
        elif giorni_licenza < 15:
            alert_messaggi.append(f"Attenzione: La licenza dello spazio scade tra {giorni_licenza} giorni.")

    # 3. Controllo Scadenza Password
    if user.data_scadenza_password:
        giorni_password = (user.data_scadenza_password - ora).days

        if giorni_password <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Accesso bloccato: Password scaduta. Contattare l'Admin di Spazio per il rinnovo."
            )
        elif giorni_password < 15:
            alert_messaggi.append(f"Attenzione: La tua password scade tra {giorni_password} giorni. Provvedi al rinnovo tramite l'Admin.")

    # 4. Autorizzazione riuscita
    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
        "ruolo": user.role.name if user.role else "Nessun ruolo",
        "alerts": alert_messaggi
    }

@app.get("/spazi/{spazio_id}")
def leggi_spazio(spazio_id: int, db: Session = Depends(get_db)):
    spazio = db.query(Spazio).filter(Spazio.id == spazio_id).first()
    if spazio is None:
        raise HTTPException(status_code=404, detail="Spazio non trovato")
        
    return {
        "id": spazio.id,
        "licenza_id": spazio.licenza_id,
        "nome_spazio": spazio.nome_spazio,
        "tipologia": spazio.tipologia
    }
