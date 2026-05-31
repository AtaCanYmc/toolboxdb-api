from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db import models, db_connector

models.Base.metadata.create_all(bind=db_connector.engine)

app = FastAPI(title="Akıllı Komponent Yönetimi - Prototip")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ı uygulamaya bağlıyoruz
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
