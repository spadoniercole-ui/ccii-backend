from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
import os

from database import engine, Base, get_db
from models import Spazio, User, Role

# Genera le tabelle nel database se non esistono
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
def home():
    return {"status": "running", "message": "API funzionante correttamente"}

@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # 1. Recupero l'utente dal database tramite l'email
    user = db.query(User).filter(User.email == credentials.username).first()

    # 2. Se l'utente non esiste, restituisco subito errore
    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # 3. Qui dovresti verificare la password (es. confrontando gli hash)
    # if not verify_password(credentials.password, user.password_hash):
    #     raise HTTPException(status_code=401, detail="Credenziali non valide")

    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
        "ruolo": user.role.name if user.role else "utente"
    }

    # Verifica utente nel Database
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali errate")
        
    # ... resto del codice ...
    ora = datetime.now(timezone.utc)
    alert_messaggi = []
    
    # [Assicurati di mantenere qui il resto della tua logica di controllo licenza/password]
    # ...
    
    return {
        "status": "success",
        "user_id": user.id,
        "email": user.email,
        "ruolo": user.role.name if user.role else "Nessun ruolo",
        "alerts": alert_messaggi
    }
    # 3. Controllo Licenza dello Spazio
    spazio = db.query(Spazio).filter(Spazio.id == user.spazio_id).first() 
    
    if spazio and spazio.data_scadenza_licenza:
        # Assicurati che le date nel DB siano aware (con timezone) per il confronto
        giorni_licenza = (spazio.data_scadenza_licenza.replace(tzinfo=timezone.utc) - ora).days
        
        if giorni_licenza <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Accesso bloccato: Licenza scaduta."
            )
        elif giorni_licenza < 15:
            alert_messaggi.append(f"Attenzione: La licenza dello spazio scade tra {giorni_licenza} giorni.")

    # 4. Controllo Scadenza Password
    if user.data_scadenza_password:
        giorni_password = (user.data_scadenza_password.replace(tzinfo=timezone.utc) - ora).days

        if giorni_password <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Accesso bloccato: Password scaduta."
            )
        elif giorni_password < 15:
            alert_messaggi.append(f"Attenzione: La tua password scade tra {giorni_password} giorni.")

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
    
    # Ora il return è correttamente allineato al blocco della funzione
    return {
        "id": spazio.id,
        "nome": spazio.nome,
        "data_scadenza": spazio.data_scadenza_licenza
    }
