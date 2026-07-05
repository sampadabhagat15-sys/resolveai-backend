from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, cases, evidence

app = FastAPI(title="ResolveAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for hackathon speed — tighten this later if time allows
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(evidence.router)


@app.get("/")
def root():
    return {"message": "ResolveAI backend is alive"}