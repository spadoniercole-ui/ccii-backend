from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 

app = FastAPI()

# Definiamo i domini autorizzati a chiamare le API
origins = [
    "https://cciiplatform.vercel.app",
    "http://localhost:3000", # Utile per testare in locale
]

# Aggiungiamo il middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Consente tutti i metodi (GET, POST, ecc.)
    allow_headers=["*"], # Consente tutti gli header
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
