# =====================================================
# MINIMAL WORKING BACKEND (FIX DEFINITIVO)
# =====================================================

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# =====================================================
# APP
# =====================================================

app = FastAPI()

# ✅ CORS (SUBITO DOPO APP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cciiplatform.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# ENDPOINTS
# =====================================================

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/login")
def login():
    return {"token": "test-token"}

# =====================================================
# START SERVER (RAILWAY)
# =====================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
