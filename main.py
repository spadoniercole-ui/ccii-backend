from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db
from models import Spazi  # Assicurati che il nome corrisponda al modello nel tuo models.py

app = FastAPI(title="Backend CCII")

# Configurazione CORS per permettere al frontend di comunicare con il backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "active", "message": "Backend CCII attivo (Modalità Isolata)"}

@app.post("/login")
def login_user():
    # Rotta temporanea di login per permettere l'accesso alla dashboard
    return {"status": "success", "token": "mock-token-superadmin"}

@app.get("/tenants")
def get_old_tenants(db: Session = Depends(get_db)):
    try:
        # 1. Lettura dei record reali dal database
        record_spazi = db.query(Spazi).all()
        
        # 2. Inizializziamo la lista per il frontend
        risposta_frontend = []
        
        # 3. Ciclo per popolare la risposta con tutte le chiavi possibili per il frontend
        for s in record_spazi:
            risposta_frontend.append({
                # Dati base dello spazio
                "id": str(s.id),
                "nome": s.nome,
                "codice": s.codice,
                "attivo": s.attivo,
                
                # Varianti per il Nome dello Spazio (Risolve l'errore N/D)
                "nome_spazio": s.nome,
                "nomeSpazio": s.nome,
                "tenant_name": s.nome,
                "name": s.nome,
                
                # Varianti per il Limite Utenti
                "max_utenti_totali": 3,
                "max_utenti": 3,
                "max_users": 3,
                "limite_utenti": 3,
                
                # Varianti per il Limite Aziende
                "max_aziende_totali": 3,
                "max_aziende": 3,
                "max_companies": 3,
                "limite_aziende": 3
            })
            
        return risposta_frontend

    except Exception as e:
        print(f"Errore durante la query dei tenants: {e}")
        return []
