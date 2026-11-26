from fastapi import FastAPI, Response

app = FastAPI(title="Mock Pagos")


@app.get("/pagos")
def listar(response: Response):
    response.headers["X-Servicio"] = "pagos"
    print("[pagos] GET /pagos recibido", flush=True)
    return {"servicio": "pagos", "id": 701, "matriculaId": 501, "valor": 150.00, "estado": "PENDIENTE"}
