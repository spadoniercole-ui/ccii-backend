@app.get("/")
def root():
    return {"status": "API ONLINE"}

# ============================================================
# CCII SAAS PLATFORM - COMPLETE VERSION
# onboarding + ruoli + pricing + multi-tenant
# ============================================================

import uuid, jwt, bcrypt, os
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel

# ============================================================
# CONFIG
# ============================================================

SECRET = os.getenv("SECRET", "secret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ccii.db")

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
    plan = Column(String)        # BASIC / PRO

# -----------------------------

class User(Base):
    __tablename__="users"
    id=Column(String, primary_key=True)
    username=Column(String,unique=True)
    password=Column(String)
    role=Column(String)          # ADMIN / USER
    tenant_id=Column(String)

# -----------------------------

class Azienda(Base):
    __tablename__="aziende"
    id=Column(String,primary_key=True)
    nome=Column(String)
    dscr=Column(Float)
    roe=Column(Float)
    tenant_id=Column(String)

# -----------------------------

class RuleSet(Base):
    __tablename__="ruleset"
    id=Column(String,primary_key=True)
    tenant_id=Column(String)
    version=Column(Integer)

class Rule(Base):
    __tablename__="rules"
    id=Column(String,primary_key=True)
    ruleset_id=Column(String)
    field=Column(String)
    operator=Column(String)
    value=Column(Float)
    result=Column(String)
    priority=Column(Integer)

# -----------------------------

class ReportHistory(Base):
    __tablename__="history"
    id=Column(String,primary_key=True)
    azienda_id=Column(String)
    score=Column(Float)
    giudizio=Column(String)
    timestamp=Column(String)

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

class RuleDTO(BaseModel):
    field: str
    operator: str
    value: float
    result: str
    priority: int

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

def get_user(token: str = Header(...)):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(401)

# ============================================================
# PRICING LOGIC
# ============================================================

def check_limit(db, tenant_id):

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    count = db.query(Azienda).filter(Azienda.tenant_id == tenant_id).count()

    if tenant.plan == "BASIC" and count >= 3:
        raise HTTPException(403, "Limite aziende piano BASIC")

# ============================================================
# ENGINE
# ============================================================

class Engine:

    def eval(self, v, op, t):
        return {
            "<": v<t,
            ">": v>t,
            "<=": v<=t,
            ">=": v>=t
        }.get(op, False)

    def calcola(self, a, rules):

        score = (a.dscr + a.roe)/2
        data = {"dscr":a.dscr,"roe":a.roe,"score":score}

        rules = sorted(rules, key=lambda x: x.priority)

        for r in rules:
            if self.eval(data[r.field], r.operator, r.value):
                return round(score,2), r.result

        return round(score,2), "N/D"

# ============================================================
# APP
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def db():
    d = SessionLocal()
    try: yield d
    finally: d.close()

# ============================================================
# ONBOARDING CLIENTE
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

    return {"status":"created"}

# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(data: LoginDTO, db: Session = Depends(db)):

    u = db.query(User).filter(User.username == data.username).first()

    if not u or not verify_pwd(data.password, u.password):
        raise HTTPException(401)

    return {"token":create_token(u)}

# ============================================================
# AZIENDE
# ============================================================

@app.get("/aziende")
def aziende(db: Session = Depends(db), u=Depends(get_user)):
    return [
        {"id":a.id,"nome":a.nome}
        for a in db.query(Azienda).filter(Azienda.tenant_id == u["tenant"])
    ]

# -----------------------------

@app.post("/azienda")
def crea(data:dict, db:Session=Depends(db), u=Depends(get_user)):

    check_limit(db, u["tenant"])

    a=Azienda(
        id=str(uuid.uuid4()),
        nome=data["nome"],
        dscr=data["dscr"],
        roe=data["roe"],
        tenant_id=u["tenant"]
    )

    db.add(a)
    db.commit()

    return {"ok":True}

# ============================================================
# RULES VERSIONING
# ============================================================

@app.post("/ruleset")
def set_rules(rules:list[RuleDTO], db:Session=Depends(db), u=Depends(get_user)):

    count=db.query(RuleSet).filter(RuleSet.tenant_id==u["tenant"]).count()

    rs=RuleSet(id=str(uuid.uuid4()),tenant_id=u["tenant"],version=count+1)
    db.add(rs)

    for r in rules:
        db.add(Rule(
            id=str(uuid.uuid4()),
            ruleset_id=rs.id,
            field=r.field,
            operator=r.operator,
            value=r.value,
            result=r.result,
            priority=r.priority
        ))

    db.commit()

    return {"version":count+1}

# ============================================================
# REPORT
# ============================================================

@app.get("/report/{id}")
def report(id:str, db:Session=Depends(db), u=Depends(get_user)):

    a=db.query(Azienda).filter(
        Azienda.id==id,
        Azienda.tenant_id==u["tenant"]
    ).first()

    rs=db.query(RuleSet).filter(
        RuleSet.tenant_id==u["tenant"]
    ).order_by(RuleSet.version.desc()).first()

    rules = db.query(Rule).filter(Rule.ruleset_id==rs.id).all() if rs else []

    s,g = Engine().calcola(a, rules)

    db.add(ReportHistory(
        id=str(uuid.uuid4()),
        azienda_id=a.id,
        score=s,
        giudizio=g,
        timestamp=str(datetime.utcnow())
    ))
    db.commit()

    return {
        "azienda":a.nome,
        "score":s,
        "giudizio":g
    }