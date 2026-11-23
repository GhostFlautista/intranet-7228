from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import hashlib
import os

app = FastAPI()

from fastapi import Request

@app.middleware("http")
async def forzar_utf8(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and "charset" not in content_type:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response



def encriptar(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()

def iniciar_bd():
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, clave TEXT, nombre TEXT, rol TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS alumnos (codigo TEXT PRIMARY KEY, nombre TEXT, grado_seccion TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS asistencias (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_alumno TEXT, fecha TEXT, hora TEXT, estado TEXT, registrado_por TEXT)")

    # Usuario Administrador solicitado + un Auxiliar de ejemplo
    usuarios_base = [
        ("MikeSanchez", encriptar("STEve123*"), "Mike Sánchez", "Administrador"),
        ("auxiliar01", encriptar("Aux7228*"), "Auxiliar de Turno", "Auxiliar")
    ]
    c.executemany("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?, ?)", usuarios_base)

    alumnos_demo = [
        ("ALU-7228-001", "Quispe Mamani, Valeria Sofía", "3° 'A' Secundaria"),
        ("ALU-7228-002", "Huamán Torres, Mateo Sebastián", "4° 'B' Secundaria"),
        ("ALU-7228-003", "Flores Chávez, Camila Andrea", "5° 'A' Primaria")
    ]
    c.executemany("INSERT OR IGNORE INTO alumnos VALUES (?, ?, ?)", alumnos_demo)
    conn.commit()
    conn.close()

iniciar_bd()

class LoginReq(BaseModel):
    usuario: str
    clave: str

class NuevoUsuarioReq(BaseModel):
    usuario: str
    clave: str
    nombre: str
    rol: str

class EscaneoQR(BaseModel):
    codigo: str
    registrado_por: str = "Sistema"

@app.get("/", response_class=HTMLResponse)
def ver_intranet():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/escudo.png")
def ver_escudo():
    if os.path.exists("escudo.png"):
        return FileResponse("escudo.png")
    return FileResponse("escudo.jpg")

@app.get("/banner_navidad.jpg")
def ver_banner():
    if os.path.exists("banner_navidad.jpg"):
        return FileResponse("banner_navidad.jpg")
    return FileResponse("banner_navidad.png")



@app.get("/html5-qrcode.min.js")
def ver_libreria_qr():
    return FileResponse("html5-qrcode.min.js", media_type="application/javascript")

@app.get("/manifest.json")
def ver_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
def ver_sw():
    return FileResponse("sw.js", media_type="application/javascript")


@app.post("/api/login")
def login(datos: LoginReq):
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    c.execute("SELECT nombre, rol FROM usuarios WHERE usuario = ? AND clave = ?", (datos.usuario, encriptar(datos.clave)))
    user = c.fetchone()
    conn.close()
    if not user:
        return {"ok": False, "mensaje": "Usuario o contraseña incorrectos"}
    return {"ok": True, "usuario": datos.usuario, "nombre": user[0], "rol": user[1]}

@app.post("/api/usuarios")
def crear_usuario(datos: NuevoUsuarioReq):
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", (datos.usuario, encriptar(datos.clave), datos.nombre, datos.rol))
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario {datos.usuario} ({datos.rol}) creado correctamente"}
    except sqlite3.IntegrityError:
        return {"ok": False, "mensaje": "Ese nombre de usuario ya existe"}
    finally:
        conn.close()

@app.post("/api/asistencia")
def registrar_asistencia(datos: EscaneoQR):
    ahora = datetime.now()
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    c.execute("SELECT nombre, grado_seccion FROM alumnos WHERE codigo = ?", (datos.codigo,))
    alumno = c.fetchone()
    if not alumno:
        conn.close()
        return {"ok": False, "mensaje": "Código no encontrado: " + datos.codigo}
    nombre, grado = alumno
    estado = "Tardanza" if (ahora.hour >= 8 and (ahora.hour > 8 or ahora.minute > 0)) else "Puntual"
    c.execute("INSERT INTO asistencias (codigo_alumno, fecha, hora, estado, registrado_por) VALUES (?, ?, ?, ?, ?)",
              (datos.codigo, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), estado, datos.registrado_por))
    conn.commit()
    conn.close()
    return {"ok": True, "codigo": datos.codigo, "nombre": nombre, "grado": grado, "hora": ahora.strftime("%H:%M:%S"), "estado": estado}

@app.get("/manifest.json")
def ver_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")

