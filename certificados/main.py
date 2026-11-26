from fastapi import FastAPI, Response

app = FastAPI(title="Mock Certificados")


@app.get("/certificados")
def listar(response: Response):
    response.headers["X-Servicio"] = "certificados"
    print("[certificados] GET /certificados recibido", flush=True)
    return {"servicio": "certificados", "id": 901, "estudianteId": 101, "tipo": "CERTIFICADO_DE_MATRICULA", "estado": "EMITIDO"}
