from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ✅ temporaneo per test assoluto
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"msg": "root works"}

@app.get("/health")
def health():
    return {"msg": "health works"}

@app.post("/login")
def login():
    return {"msg": "login works"}
