from fastapi import FastAPI
from app.routers import auth, cases, evidence

app = FastAPI(title="ResolveAI API")

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)


@app.get("/")
def root():
    return {"message": "ResolveAI backend is alive"}