from fastapi import FastAPI, Response

app = FastAPI(title="Mock Estudiantes")


@app.get("/estudiantes")
def listar(response: Response):
    response.headers["X-Servicio"] = "estudiantes"
    print("[estudiantes] GET /estudiantes recibido", flush=True)
    return {"servicio": "estudiantes", "id": 101, "nombre": "Ana Perez"}
