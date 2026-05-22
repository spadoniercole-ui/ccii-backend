# ============================================================# PLATFORM - VERSIONE DEFINITIVA (CORS STABILE)
# ============================================================

import uuid, jwt, bcrypt, os
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel

# ============================================================
# CONFIG
# ============================================================

SECRET = os.getenv("SECRET", "secret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ccii.db")

SUPERADMIN_USERNAME = "SuperAdmin"
SUPERADMIN_PASSWORD = "CCIIWeb2.0"

# ============================================================
# DATABASE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ============================================================
# MODELS
# ============================================================

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String)
    plan = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String)
    tenant_id = Column(String)

class Azienda(Base):
    __tablename__ = "aziende"
    id = Column(String, primary_key=True)
    nome = Column(String)
    dscr = Column(Float)
    roe = Column(Float)
    tenant_id = Column(String)

Base.metadata.create_all(bind=engine)

# ============================================================
# SCHEMAS
# ============================================================

class LoginDTO(BaseModel):
    username: str
    password: str

# ============================================================
# AUTH UTILS
# ============================================================

def hash_pwd(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_pwd(p,h): return bcrypt.checkpw(p.encode(), h.encode())

def create_token(payload: dict):
    return jwt.encode({
        **payload,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }, SECRET, algorithm="HS256")

def get_user(token: str = None):
    if not token:
        raise HTTPException(401)
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(401)

def is_super_admin(u):
    return u.get("role") == "SUPER_ADMIN"

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()

# 🔥 CORS DEFINITIVO (QUESTO RISOLVE IL TUO ERRORE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ✅ in debug / produzione iniziale
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False    # ✅ ESSENZIALE per evitare conflitti browser
)

# ============================================================
# DB SESSION
# ============================================================

def db():
    d = SessionLocal()
    try:
        yield d
    finally:
        d.close()

# ============================================================
# HEALTHCHECK (RAILWAY)
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}

# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {"status": "API OK"}

# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(data: LoginDTO, db: Session = Depends(db)):

    # ✅ SUPER ADMIN HARDCODED
    if data.username == SUPERADMIN_USERNAME and data.password == SUPERADMIN_PASSWORD:
        token = create_token({
            "sub": "superadmin",
            "tenant": "GLOBAL",
            "role": "SUPER_ADMIN"
        })
        return {"token": token}

    # ✅ NORMAL USER
    u = db.query(User).filter(User.username == data.username).first()

    if not u or not verify_pwd(data.password, u.password):
        raise HTTPException(401)

    return {
        "token": create_token({
            "sub": u.id,
            "tenant": u.tenant_id,
            "role": u.role
        })
    }

# ============================================================
# TENANTS
# ============================================================

@app.get("/tenants")
def get_tenants(db: Session = Depends(db), user=Depends(get_user)):
    if not is_super_admin(user):
        raise HTTPException(403)
    return db.query(Tenant).all()

# ============================================================
# AZIENDE
# ============================================================

@app.get("/aziende")
def get_aziende(db: Session = Depends(db), user=Depends(get_user)):

    if is_super_admin(user):
        data = db.query(Azienda).all()
    else:
        data = db.query(Azienda).filter(Azienda.tenant_id == user["tenant"])

    return [
        {"id": a.id, "nome": a.nome, "tenant_id": a.tenant_id}
        for a in data
    ]
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
