from fastapi import FastAPI, HTTPExceptionfrom fastapi import FastAPI, HTTP.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# TEST ENDPOINT
# =====================================================

@app.get("/health")
def health():
    return {"status": "ok"}

# =====================================================
# LOGIN (solo test per isolare problema)
# =====================================================

@app.post("/login")
def login():
    return {"token": "test"}

# =====================================================
# START (Railway)
# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# =====================================================
# APP
# =====================================================

app = FastAPI()

# ✅ CORS (prima di tutto)
app.add_middleware(
    CORSMiddleware,
