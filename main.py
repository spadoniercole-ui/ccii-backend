# ============================================================
# CCII SAAS PLATFORM COMPLETA (FIX CORS + PRE-FLIGHT)
# ============================================================

import uuid, jwt, bcrypt, os
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Float, Integer
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
# DTO
# ============================================================

class LoginDTO(BaseModel):
    username: str
    password: str

class OnboardingDTO(BaseModel):
    name: str
    username: str
    password: str

# ============================================================
# AUTH
# ============================================================

def hash_pwd(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_pwd(p,h): return bcrypt.checkpw(p.encode(), h.encode())

def create_token(user):
    return jwt.encode({
        "sub": user.id,
        "tenant": user.tenant_id,
        "role": user.role,
        "exp": datetime.utcnow()+timedelta(hours=8)
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
# APP
# ============================================================

app = FastAPI()

# ✅ CORS FIX CORRETTO
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cciiplatform.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ FIX PRE-FLIGHT (RISOLVE 502)
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    return {}

# ============================================================
# DB SESSION
# ============================================================

def db():
    d = SessionLocal()
    try: yield d
    finally: d.close()

# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(data: LoginDTO, db: Session = Depends(db)):

    # ✅ SUPER ADMIN HARDCODED
    if data.username == SUPERADMIN_USERNAME and data.password == SUPERADMIN_PASSWORD:
        token = jwt.encode({
            "sub": "superadmin",
            "tenant": "GLOBAL",
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow()+timedelta(hours=8)
        }, SECRET, algorithm="HS256")

        return {"token": token}

    # ✅ USER NORMALE
    u = db.query(User).filter(User.username == data.username).first()

    if not u or not verify_pwd(data.password, u.password):
        raise HTTPException(401)

    return {"token": create_token(u)}

# ============================================================
# ONBOARDING
# ============================================================

@app.post("/onboarding")
def onboarding(data: OnboardingDTO, db: Session = Depends(db)):

    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=data.name,
        plan="BASIC"
    )

    user = User(
        id=str(uuid.uuid4()),
        username=data.username,
        password=hash_pwd(data.password),
        role="ADMIN",
        tenant_id=tenant.id
    )

    db.add(tenant)
    db.add(user)
    db.commit()

    return {"status": "created"}

# ============================================================
# TENANTS (SUPER ADMIN)
# ============================================================

@app.get("/tenants")
def tenants(db: Session = Depends(db), token=Depends(get_user)):

    if not is_super_admin(token):
        raise HTTPException(403)

    return [
        {"id": t.id, "name": t.name, "plan": t.plan}
        for t in db.query(Tenant).all()
    ]

# ============================================================
# CHANGE PLAN
# ============================================================

@app.post("/tenant/{id}/plan")
def change_plan(id: str, plan: str, db: Session = Depends(db), token=Depends(get_user)):

    if not is_super_admin(token):
        raise HTTPException(403)

    t = db.query(Tenant).filter(Tenant.id == id).first()

    if not t:
        raise HTTPException(404)

    t.plan = plan.upper()
    db.commit()

    return {"ok": True}

# ============================================================
# AZIENDE
# ============================================================

@app.get("/aziende")
def aziende(db: Session = Depends(db), token=Depends(get_user)):

    if is_super_admin(token):
        aziende = db.query(Azienda).all()
    else:
        aziende = db.query(Azienda).filter(Azienda.tenant_id == token["tenant"])

    return [
        {"id": a.id, "nome": a.nome, "tenant_id": a.tenant_id}
        for a in aziende
    ]

@app.post("/azienda")
def crea(data: dict, db: Session = Depends(db), token=Depends(get_user)):

    tenant_id = data.get("tenant_id") if is_super_admin(token) else token["tenant"]

    a = Azienda(
        id=str(uuid.uuid4()),
        nome=data["nome"],
        dscr=data["dscr"],
        roe=data["roe"],
        tenant_id=tenant_id
    )

    db.add(a)
    db.commit()

    return {"ok": True}

# ============================================================
# TEST ROOT
# ============================================================

@app.get("/")
def root():
    return {"status": "API ONLINE"}
