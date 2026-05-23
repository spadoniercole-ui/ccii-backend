# =====================================================
# CCII BACKEND - BASE STABILE
# =====================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import json

# =====================================================
# APP
# =====================================================

app = FastAPI()

# ✅ CORS OK PER VERCEL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cciiplatform.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# SCHEMI
# =====================================================

class LoginRequest(BaseModel):
    username: str
    password: str

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():
    return {"status": "ok"}

# =====================================================
# LOGIN
# =====================================================

@app.post("/login")
def login(req: LoginRequest):

    # ✅ SUPER ADMIN
    if req.username == "SuperAdmin" and req.password == "CCIIWeb2.0":

        payload = {
            "role": "SUPER_ADMIN"
        }

        # creiamo token "tipo JWT" leggibile dal frontend
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        fake_token = f"xxx.{payload_b64}.xxx"

        return {
            "token": fake_token
        }

    # ❌ credenziali errate
    raise HTTPException(status_code=401, detail="Credenziali non valide")

# =====================================================
# API SUPER ADMIN
# =====================================================

@app.get("/superadmin")
def superadmin_dashboard():

    # dati finti per test UI
    return {
        "tenants": [
            {"id": "1", "name": "Cliente A", "plan": "BASIC"},
            {"id": "2", "name": "Cliente B", "plan": "PRO"}
        ]
    }
``
