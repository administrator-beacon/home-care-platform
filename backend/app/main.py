from fastapi import FastAPI

from app.api import auth, roles, users
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
@app.get("/health")
def health():
    return {"status": "ok"}

