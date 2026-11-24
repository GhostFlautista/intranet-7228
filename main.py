import os
import sqlite3
import hashlib
from datetime import datetime, time
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    usuarios_base = [
        ("MikeSanchez", encriptar("STEve123*"), "Mike Sánchez", "Administrador"),
        ("GonzaloSembrera", encriptar("GonzaSem123*"), "Gonzalo Sembrera", "Auxiliar"),
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

def evaluar_turno_y_estado(hora_actual: time, turno: str) -> str:
    if turno == "Tarde":
        if hora_actual <= time(13, 5, 59):
            return "Puntual (Tarde)"
        elif hora_actual <= time(14, 30, 59):
            return "Tardanza (Tarde)"
        elif hora_actual >= time(18, 10, 0):
            return "Salida (Tarde)"
        else:
            return "Fuera de Horario (Tarde)"
    else:
        # Turno Mañana (por defecto)
        if hora_actual <= time(8, 5, 59):
            return "Puntual (Mañana)"
        elif hora_actual <= time(10, 0, 59):
            return "Tardanza (Mañana)"
        elif hora_actual >= time(12, 45, 0):
            return "Salida (Mañana)"
        else:
            return "Fuera de Horario (Mañana)"

class LoginReq(BaseModel):
    usuario: str
    clave: str

class NuevoUsuarioReq(BaseModel):
    solicitante: str = ""
    usuario: str
    clave: str
    nombre: str
    rol: str

class AsistenciaReq(BaseModel):
    codigo: str
    registrado_por: str = "Sistema"
    hora_reloj: str = ""
    turno: str = "Mañana"

@app.get("/", response_class=HTMLResponse)
def ver_intranet():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/escudo.png")
def ver_escudo():
    return FileResponse("escudo.png" if os.path.exists("escudo.png") else "escudo.jpg")

@app.get("/banner_navidad.jpg")
def ver_banner():
    return FileResponse("banner_navidad.jpg" if os.path.exists("banner_navidad.jpg") else "banner_navidad.png")

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
    return {"ok": True, "usuario": datos.usuario, "nombre": user, "rol": user}

@app.post("/api/usuarios")
def crear_usuario(datos: NuevoUsuarioReq):
    if datos.solicitante != "MikeSanchez":
        return {"ok": False, "mensaje": "Acceso denegado: Solo MikeSanchez tiene permisos CRUD."}
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
def registrar_asistencia(datos: AsistenciaReq):
    ahora_peru = datetime.now(ZoneInfo("America/Lima"))
    fecha_str = ahora_peru.strftime("%Y-%m-%d")

    try:
        hora_actual = datetime.strptime(datos.hora_reloj.strip(), "%H:%M:%S").time()
    except Exception:
        hora_actual = ahora_peru.time().replace(microsecond=0)

    hora_str = hora_actual.strftime("%H:%M:%S")
    estado = evaluar_turno_y_estado(hora_actual, datos.turno)

    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    c.execute("SELECT nombre, grado_seccion FROM alumnos WHERE codigo = ?", (datos.codigo.strip(),))
    alumno = c.fetchone()

    if not alumno:
        conn.close()
        return {"ok": False, "mensaje": f"Código QR no registrado: {datos.codigo}"}

    nombre, grado = alumno, alumno
    c.execute(
        "INSERT INTO asistencias (codigo_alumno, fecha, hora, estado, registrado_por) VALUES (?, ?, ?, ?, ?)",
        (datos.codigo.strip(), fecha_str, hora_str, estado, datos.registrado_por)
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "codigo": datos.codigo.strip(),
        "nombre": nombre,
        "grado": grado,
        "hora": hora_str,
        "estado": estado
    }
