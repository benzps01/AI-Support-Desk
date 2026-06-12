from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Support Desk API",
    description="Backend API for AI-assisted support ticketing",
    version="1.0.0"
)

# Set up CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """ Health check endpoint """
    return {"status": "ok", "message": "API is running successfully"}