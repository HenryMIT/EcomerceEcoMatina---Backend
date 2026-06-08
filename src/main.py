from fastapi import FastAPI

app = FastAPI(
    title="API EcoMatina",
    description="API para gestión de electrodomésticos y equipos de cocina",
    version="1.0.0"
    )

@app.get("/")
def root():
    return {"mensaje": "API EcoMatina funcionando correctamente"}

