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
    c.execute("CREATE TABLE IF NOT EXISTS padre_alumno (usuario_padre TEXT, codigo_alumno TEXT, PRIMARY KEY (usuario_padre, codigo_alumno))")

    usuarios_base = [
        ("MikeSanchez", encriptar("STEve123*"), "Mike Sánchez", "Administrador"),
        ("GonzaloSembrera", encriptar("GonzaSem123*"), "Gonzalo Sembrera", "Auxiliar"),
        ("auxiliar01", encriptar("Aux7228*"), "Auxiliar de Turno", "Auxiliar"),
        ("PadreQuispe", encriptar("Padre7228*"), "Sr. Carlos Quispe (Apoderado)", "Padre")
    ]
    c.executemany("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?, ?)", usuarios_base)

    alumnos_demo = [
        ("ALU-7228-001", "Quispe Mamani, Valeria Sofía", "3° 'A' Secundaria"),
        ("ALU-7228-002", "Huamán Torres, Mateo Sebastián", "4° 'B' Secundaria"),
        ("ALU-7228-003", "Flores Chávez, Camila Andrea", "5° 'A' Primaria")
    ]
    c.executemany("INSERT OR IGNORE INTO alumnos VALUES (?, ?, ?)", alumnos_demo)

    # Vincular al padre de ejemplo con su hija ALU-7228-001
    c.execute("INSERT OR IGNORE INTO padre_alumno VALUES (?, ?)", ("PadreQuispe", "ALU-7228-001"))

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
    codigo_hijo: str = ""

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

@app.get("/peruano_canadiense.jpg")
def ver_fondo_colegio():
    return FileResponse("peruano_canadiense.jpg")

@app.get("/fondo_app.jpg")
def ver_fondo_app():
    return FileResponse("fondo_app.jpg" if os.path.exists("fondo_app.jpg") else "fondo_app.png")

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
        return {"ok": False, "mensaje": "Nueva versión 2.2 disponible: Reporte Excel completo con todas las columnas y datos."}
    return {"ok": True, "usuario": datos.usuario, "nombre": user[0], "rol": user[1]}

@app.post("/api/usuarios")
def crear_usuario(datos: NuevoUsuarioReq):
    if datos.solicitante != "MikeSanchez":
        return {"ok": False, "mensaje": "Nueva versión 2.2 disponible: Reporte Excel completo con todas las columnas y datos."}
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", (datos.usuario, encriptar(datos.clave), datos.nombre, datos.rol))
        if datos.rol == "Padre" and datos.codigo_hijo.strip():
            for cod_h in datos.codigo_hijo.split(","):
                if cod_h.strip():
                    c.execute("INSERT OR IGNORE INTO padre_alumno VALUES (?, ?)", (datos.usuario, cod_h.strip()))
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario {datos.usuario} ({datos.rol}) creado correctamente"}
    except sqlite3.IntegrityError:
        return {"ok": False, "mensaje": "Nueva versión 2.2 disponible: Reporte Excel completo con todas las columnas y datos."}
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

    nombre, grado = alumno[0], alumno[1]
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

@app.get("/api/padre/asistencias/{usuario_padre}")
def obtener_asistencias_padre(usuario_padre: str):
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()
    c.execute("""
        SELECT a.id, al.codigo, al.nombre, al.grado_seccion, a.fecha, a.hora, a.estado
        FROM asistencias a
        JOIN padre_alumno pa ON a.codigo_alumno = pa.codigo_alumno
        JOIN alumnos al ON al.codigo = a.codigo_alumno
        WHERE pa.usuario_padre = ?
        ORDER BY a.id DESC
        LIMIT 20
    """, (usuario_padre,))
    filas = c.fetchall()
    conn.close()

    registros = []
    for f in filas:
        registros.append({
            "id": f[0],
            "codigo": f[1],
            "nombre": f[2],
            "grado": f[3],
            "fecha": f[4],
            "hora": f[5],
            "estado": f[6]
        })
    return {"ok": True, "registros": registros}

@app.get("/api/version")
def verificar_version():
    return {
        "version": "2.2",
        "obligatoria": False,
        "mensaje": "Nueva versión 2.2 disponible: Reporte Excel completo con todas las columnas y datos.",
        "texto_turno_tarde": "Turno Tarde (Ingreso 1:00pm | Salida 6:10pm)"
    }

from io import BytesIO
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from io import BytesIO
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

@app.get("/api/reporte/excel")
def descargar_reporte_excel(fecha: str = "", grado: str = ""):
    conn = sqlite3.connect("asistencia_7228.db")
    c = conn.cursor()

    query = """
        SELECT a.fecha, a.hora, a.codigo_alumno,
               COALESCE(al.nombre, 'Estudiante No Registrado'),
               COALESCE(al.grado_seccion, '-'),
               a.estado, a.registrado_por
        FROM asistencias a
        LEFT JOIN alumnos al ON TRIM(al.codigo) = TRIM(a.codigo_alumno)
        WHERE 1=1
    """
    params = []
    if fecha.strip():
        query += " AND a.fecha = ?"
        params.append(fecha.strip())
    if grado.strip():
        query += " AND al.grado_seccion LIKE ?"
        params.append(f"%{grado.strip()}%")

    query += " ORDER BY COALESCE(al.nombre, a.codigo_alumno) ASC, a.fecha DESC, a.hora ASC"
    c.execute(query, params)
    filas = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asistencia 7228"

    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    encabezados = ["Día", "Fecha", "Hora", "Código", "Estudiante", "Grado y Sección", "Estado", "Registrado por"]
    ws.append(encabezados)

    header_fill = PatternFill(start_color="0033CC", end_color="0033CC", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx in range(1, len(encabezados) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for f in filas:
        fecha_val, hora_val, cod_val, nom_val, grado_val, est_val, reg_val = f
        try:
            dt = datetime.strptime(fecha_val, "%Y-%m-%d")
            dia_nombre = dias_es[dt.weekday()]
        except Exception:
            dia_nombre = ""
        ws.append([dia_nombre, fecha_val, hora_val, cod_val, nom_val, grado_val, est_val, reg_val])

    ultima_fila = max(len(filas) + 1, 2)
    ws.auto_filter.ref = f"A1:H{ultima_fila}"

    anchos = {"A": 14, "B": 14, "C": 12, "D": 16, "E": 34, "F": 22, "G": 22, "H": 18}
    for col_letra, ancho in anchos.items():
        ws.column_dimensions[col_letra].width = ancho

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    nombre_archivo = f"Reporte_Asistencia_7228_{fecha if fecha else 'Completo'}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )
