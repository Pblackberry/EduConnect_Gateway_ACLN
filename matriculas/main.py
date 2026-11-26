from fastapi import FastAPI, Response

app = FastAPI(title="Mock Matrículas")


@app.get("/matriculas")
def listar(response: Response):
    response.headers["X-Servicio"] = "matriculas"
    print("[matriculas] GET /matriculas recibido", flush=True)
    return {"servicio": "matriculas", "id": 501, "estudianteId": 101, "estado": "ACTIVA"}
