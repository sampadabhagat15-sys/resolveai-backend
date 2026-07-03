from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="ResolveAI API")

app.include_router(auth.router)


@app.get("/")
def root():
    return {"message": "ResolveAI backend is alive"}