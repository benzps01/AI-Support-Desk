from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.tickets import router as tickets_router

app = FastAPI(
    title="AI Support Desk API",
    description="Backend API for AI-assisted support ticketing",
    version="1.0.0"
)

# Set up CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
    "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# we officially mount our auth endpoints
app.include_router(auth_router)
app.include_router(tickets_router)

@app.get("/health")
async def health_check():
    """ Health check endpoint """
    return {"status": "ok", "message": "API is running successfully"}