# -*- coding: utf-8 -*-
"""
MI SEMANA — "Tu vida entera en una semana realista"
Fase 1 · Lógica Original Completa + Diseño App
"""

import json
import sqlite3
from datetime import date, timedelta
import streamlit as st

DB = "mi_semana.db"

# 1. Configuración Mobile-First
st.set_page_config(
    page_title="Mi Semana",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. CSS de App (Colores originales, diseño moderno)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #FBF7F0; }
    .block-container { padding-top: 1.5rem; padding-bottom: 6rem; max-width: 600px; }
    
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }

    .hero {
        background: linear-gradient(135deg, #1F6F5C, #2E8B74);
        padding: 20px 24px; border-radius: 20px; color: #fff; margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(31,111,92,.2); text-align: center;
    }
    .hero-title { font-size: 24px; font-weight: 800; margin: 0; }
    .hero-sub { font-size: 14px; opacity: .9; margin-top: 5px; }

    .card {
        background: #fff; border-radius: 16px; padding: 16px 18px;
        box-shadow: 0 4px 14px rgba(0,0,0,.05); border: 1px solid #EFE7DA; margin-bottom: 12px;
    }
    .card-num { font-size: 26px; font-weight: 800; color: #1F6F5C; }
    .card-lbl { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #8A8071; }
    .card-pie { font-size: 13px; color: #5C564C; margin-top: 4px; }

    div.stButton > button {
        background-color: #fff; color: #1F6F5C; border: 1px solid #E4D9C6;
        border-radius: 12px; padding: 8px 2px; width: 100%; font-weight: 700; font-size: 11px;
        transition: all 0.2s;
    }
    div.stButton > button[kind="primary"] {
        background-color: #1F6F5C; color: #fff; border: none; box-shadow: 0 4px 10px rgba(31,111,92,0.3);
    }
    div[data-testid="stForm"] { background: #fff; border-radius: 16px; padding: 15px; border: 1px solid #EFE7DA; }
</style>
""", unsafe_allow_html=True)

# 3. Base de Datos (ESQUEMA ORIGINAL RESTAURADO)
AREAS_DEFECTO = [
    ("Trabajo", "💼"), ("Hogar", "🏠"), ("Familia", "👨‍👩‍👧"),
    ("Pareja", "💞"), ("Salud", "🩺"), ("Hobbies", "🎨"),
    ("Aprendizaje", "📚"), ("Descanso", "🌙"),
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL,
  emoji TEXT DEFAULT '🌱', meta TEXT DEFAULT '', activa INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS proyectos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, area_id INTEGER, nombre TEXT NOT NULL,
  nota TEXT DEFAULT '', estado TEXT DEFAULT 'activo', creado TEXT
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, tipo TEXT DEFAULT 'tarea',
  area_id INTEGER, proyecto_id INTEGER, fecha TEXT, duracion_min INTEGER DEFAULT 30,
  energia TEXT DEFAULT 'Media', prioridad INTEGER DEFAULT 0, estado TEXT DEFAULT 'pendiente', creado TEXT
);
CREATE TABLE IF NOT EXISTS semanas (
  inicio TEXT PRIMARY KEY, capacidad TEXT DEFAULT '{}', prioridades TEXT DEFAULT '[]', nota TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS revisiones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, funciono TEXT, sobro TEXT, abandono TEXT, animo INTEGER, creado TEXT
);
"""

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def ejecutar(sql, params=()):
    c = conn()
    cur = c.execute(sql, params)
    c.commit()
    last = cur.lastrowid
    c.close()
    return last

def consultar(sql, params=()):
    c = conn()
    rows = c.execute(sql, params).fetchall()
    c.close()
    return rows

def init_db():
    c = conn()
    c.executescript(ESQUEMA)
    c.commit()
    total = c.execute("SELECT COUNT(*) c FROM areas").fetchone()["c"]
    if total == 0:
        c.executemany("INSERT INTO areas (nombre, emoji) VALUES (?,?)", AREAS_DEFECTO)
        c.commit()
    c.close()

def cfg_get(clave, default=None):
    row = consultar("SELECT valor FROM config WHERE clave=?", (clave,))
    return json.loads(row[0]["valor"]) if row else default

def cfg_set(clave, valor):
    ejecutar(
        "INSERT INTO config(clave,valor) VALUES(?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, json.dumps(valor, ensure_ascii=False)),
    )

def areas():
    return consultar("SELECT * FROM areas WHERE activa=1 ORDER BY id")

def lunes(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())

def fecha_es(d):
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dias[d.weekday()]} {d.day} {meses[d.month - 1]}"

def capacidad_semana(inicio):
    row = consultar("SELECT capacidad FROM semanas WHERE inicio=?", (inicio,))
    if not row: return {}
    crudo = json.loads(row[0]["capacidad"] or "{}")
    return {int(k): v for k, v in crudo.items()}

def carga_semana(inicio, fin):
    rows = consultar(
        "SELECT area_id, COALESCE(SUM(duracion_min),0) m FROM items "
        "WHERE estado='pendiente' AND fecha BETWEEN ? AND ? GROUP BY area_id", (inicio, fin),
    )
    return {r["area_id"]: r["m"] for r in rows}

def guardar_semana(inicio, capacidad=None, prioridades=None, nota=None):
    row = consultar("SELECT * FROM semanas WHERE inicio=?", (inicio,))
    actual = dict(row[0]) if row else {"inicio": inicio, "capacidad": "{}", "prioridades": "[]", "nota": ""}
    if capacidad is not None: actual["capacidad"] = json.dumps(capacidad)
    if prioridades is not None: actual["prioridades"] = json.dumps(prioridades)
    if nota is not None: actual["nota"] = nota
    ejecutar(
        "INSERT OR REPLACE INTO semanas (inicio, capacidad, prioridades, nota) VALUES (?,?,?,?)",
        (inicio, actual["capacidad"], actual["prioridades"], actual["nota"]),
    )

init_db()

# 4. Funciones UI
def hero(titulo, subtitulo, emoji="🌿"):
    st.markdown(
        f'<div class="hero"><div style="font-size:32px; margin-bottom:5px;">{emoji}</div><div class="hero-title">{titulo}</div><div class="hero-sub">{subtitulo}</div></div>',
        unsafe_allow_html=True,
    )

def tarjeta(col, etiqueta, valor, pie=""):
    col.markdown(
        f'<div class="card" style="text-align:center;"><div class="card-lbl">{etiqueta}</div><div class="card-num">{valor}</div><div class="card-pie">{pie}</div></div>',
        unsafe_allow_html=True,
    )

# 5. Vistas
if "pagina" not in st.session_state:
    st.session_state.pagina = "hoy"

if not cfg_get("onboarding"):
    hero("Mi Semana", "Tu vida entera en una semana realista.", "🌿")
    with st.form("onb"):
        nombre = st.text_input("¿Cómo te llamas?", placeholder="Ej: Camila")
        ciudad = st.text_input("¿Dónde vives?", value="Santander de Quilichao")
        horas = st.slider("¿Cuántas horas reales tienes a la semana?", 5, 80, 35, 5)
        if st.form_submit_button("Empezar 🌱"):
            cfg_set("nombre", nombre.strip() or "Vecino")
            cfg_set("ciudad", ciudad.strip())
            cfg_set("capacidad_default", horas)
            cfg_set("onboarding", True)
            st.rerun()
    st.stop()

nombre = cfg_get("nombre")
hoy = date.today()
inicio = lunes(hoy)
fin = inicio + timedelta(days=6)

if st.session_state.pagina == "hoy":
    hero(f"Hola, {nombre} 👋", f"{fecha_es(hoy).capitalize()} · {cfg_get('ciudad')}", "🌿")

    with st.form("captura_rapida", clear_on_submit=True):
        texto = st.text_input("Captura rápida", placeholder="Escribe algo y presiona Enter…", label_visibility="collapsed")
        if st.form_submit_button("Guardar en bandeja ✨"):
            if texto.strip():
                ejecutar("INSERT INTO items (titulo, tipo, creado) VALUES (?,?,?)", (texto.strip(), "tarea", hoy.isoformat()))
                st.rerun()

    pendientes = consultar("SELECT COUNT(*) c FROM items WHERE estado='pendiente'")[0]["c"]
    prios = consultar("SELECT * FROM items WHERE estado='pendiente' AND fecha=? AND prioridad>0 ORDER BY prioridad", (hoy.isoformat(),))
    cap = capacidad_semana(inicio.isoformat())
    total_cap_min = sum(cap.values()) * 60
    carga = sum(carga_semana(inicio.isoformat(), fin.isoformat()).values())

    c1, c2, c3 = st.columns(3)
    tarjeta(c1, "Pendientes", pendientes, "en tus áreas")
    if total_cap_min: tarjeta(c2, "Semana", f"{carga / total_cap_min * 100:.0f}%", "usada")
    else: tarjeta(c2, "Semana", "—", "sin capacidad")
    tarjeta(c3, "Prioridades", f"{len(prios)}/3", "para hoy")

    st.markdown("### 🎯 Mis 3 prioridades de hoy")
    if not prios: st.info("Aún no eliges. Máximo 3.")
    for p in prios:
        fila = consultar("SELECT emoji FROM areas WHERE id=?", (p["area_id"],))
        emoji = fila[0]["emoji"] if fila else "🌱"
        a, b, c = st.columns([0.6, 0.2, 0.2])
        a.markdown(f"**{p['prioridad']}.** {emoji} {p['titulo']}  \n<span style='color:#8A8071;font-size:12px'>{p['duracion_min']} min · {p['energia']}</span>", unsafe_allow_html=True)
        if b.button("✔", key=f"hecho_{p['id']}"):
            ejecutar("UPDATE items SET estado='hecho' WHERE id=?", (p["id"],)); st.rerun()
        if c.button("⏭", key=f"rep_{p['id']}"):
            ejecutar("UPDATE items SET fecha=?, prioridad=0 WHERE id=?", ((hoy + timedelta(days=1)).isoformat(), p["id"])); st.rerun()

    with st.expander("➕ Cambiar prioridades", expanded=not prios):
        opciones = consultar("SELECT id, titulo FROM items WHERE estado='pendiente' AND (fecha IS NULL OR fecha<=?)", (hoy.isoformat(),))
        labels = {r["id"]: r["titulo"] for r in opciones}
        sel = st.multiselect("Máximo 3.", list(labels.keys()), default=[p["id"] for p in prios], format_func=lambda i: labels[i], max_selections=3)
        if st.button("Fijar prioridades"):
            ejecutar("UPDATE items SET prioridad=0 WHERE fecha=?", (hoy.isoformat(),))
            for n, item_id in enumerate(sel, 1):
                ejecutar("UPDATE items SET fecha=?, prioridad=? WHERE id=?", (hoy.isoformat(), n, item_id))
            st.rerun()

elif st.session_state.pagina == "capturar":
    hero("Capturar", "Saca todo de la cabeza.", "✍️")
    lista_areas = areas()
    etiquetas = [f"{a['emoji']} {a['nombre']}" for a in lista_areas]
    mapa = {et: a["id"] for et, a in zip(etiquetas, lista_areas)}

    with st.form("nuevo_item", clear_on_submit=True):
        titulo = st.text_input("¿Qué es?")
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", ["tarea", "compromiso", "rutina"])
        area_et = c2.selectbox("Área", etiquetas)
        c3, c4 = st.columns(2)
        fecha = c3.date_input("¿Para cuándo?", value=hoy)
        dur = c4.number_input("Duración (min)", 5, 480, 30, 5)
        if st.form_submit_button("Guardar 🌿"):
            if titulo.strip():
                ejecutar("INSERT INTO items (titulo, tipo, area_id, fecha, duracion_min, creado) VALUES (?,?,?,?,?,?)",
                         (titulo.strip(), tipo, mapa[area_et], fecha.isoformat(), int(dur), hoy.isoformat()))
                st.rerun()

    st.markdown("### 📥 Bandeja")
    bandeja = consultar("SELECT * FROM items WHERE estado='pendiente' AND (fecha IS NULL OR fecha='')")
    if not bandeja: st.caption("Vacía. Respira 😌")
    for b in bandeja:
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        c1.write(f"• {b['titulo']}")
        if c2.button("Hoy", key=f"bh_{b['id']}"):
            ejecutar("UPDATE items SET fecha=? WHERE id=?", (hoy.isoformat(), b["id"])); st.rerun()
        if c3.button("🗑", key=f"bd_{b['id']}"):
            ejecutar("UPDATE items SET estado='archivado' WHERE id=?", (b["id"],)); st.rerun()

elif st.session_state.pagina == "areas":
    hero("Áreas de vida", "Las partes de tu vida.", "🧩")
    for a in areas():
        pend = consultar("SELECT COUNT(*) c FROM items WHERE estado='pendiente' AND area_id=?", (a["id"],))[0]["c"]
        with st.expander(f"{a['emoji']} {a['nombre']} · {pend} pendientes"):
            meta = st.text_input("Meta", value=a["meta"] or "", key=f"meta_{a['id']}")
            if st.button("Guardar", key=f"gm_{a['id']}"):
                ejecutar("UPDATE areas SET meta=? WHERE id=?", (meta, a["id"])); st.toast("Guardado")

elif st.session_state.pagina == "proyectos":
    hero("Proyectos", "Cosas grandes de más de un día.", "📁")
    lista_areas = areas()
    etiquetas = [f"{a['emoji']} {a['nombre']}" for a in lista_areas]
    mapa = {et: a["id"] for et, a in zip(etiquetas, lista_areas)}
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del proyecto")
        area_et = st.selectbox("Área", etiquetas)
        if st.form_submit_button("Crear proyecto"):
            if nombre_p.strip():
                ejecutar("INSERT INTO proyectos (area_id, nombre, creado) VALUES (?,?,?)", (mapa[area_et], nombre_p.strip(), hoy.isoformat()))
                st.rerun()
                
    for p in consultar("SELECT * FROM proyectos WHERE estado='activo'"):
        tareas = consultar("SELECT COUNT(*) c FROM items WHERE proyecto_id=? AND estado='pendiente'", (p["id"],))[0]["c"]
        st.markdown(f"<div class='card'><b>{p['nombre']}</b><br><span style='color:#888;font-size:12px'>{tareas} tareas abiertas</span></div>", unsafe_allow_html=True)

elif st.session_state.pagina == "plan":
    hero("Plan Semanal", "Decide antes de que empiece.", "🗓️")
    st.session_state.setdefault("offset_semana", 0)
    inicio_s = lunes() + timedelta(weeks=st.session_state["offset_semana"])
    fin_s = inicio_s + timedelta(days=6)
    
    b1, _, b3 = st.columns([0.25, 0.5, 0.25])
    if b1.button("← Antes"): st.session_state["offset_semana"] -= 1; st.rerun()
    if b3.button("Después →"): st.session_state["offset_semana"] += 1; st.rerun()

    ini_iso, fin_iso = inicio_s.isoformat(), fin_s.isoformat()
    cap = capacidad_semana(ini_iso)
    carga = carga_semana(ini_iso, fin_iso)

    st.markdown(f"**Semana del {fecha_es(inicio_s)} al {fecha_es(fin_s)}**")
    
    with st.form("capacidad"):
        st.caption("Define cuántas horas tienes por área.")
        nuevas = {}
        cols = st.columns(4)
        for i, a in enumerate(areas()):
            with cols[i % 4]: nuevas[str(a["id"])] = st.number_input(f"{a['emoji']} {a['nombre']}", 0, 80, int(cap.get(a["id"], 0)), 1, key=f"cap_{a['id']}")
        if st.form_submit_button("Guardar capacidad"):
            guardar_semana(ini_iso, capacidad={k: v for k, v in nuevas.items() if v > 0}); st.rerun()

    total_cap, total_carga = sum(cap.values()) * 60, sum(carga.values())
    if total_cap:
        pct = total_carga / total_cap
        if pct > 1: st.error("🚨 Semana sobrecargada. Algo tiene que salir.")
        elif pct > 0.85: st.warning("⚠️ Semana justa.")
        else: st.success("✅ Humanamente posible.")

elif st.session_state.pagina == "revision":
    hero("Revisión", "Cierra la semana sin culpa.", "🔄")
    with st.form("rev"):
        f1 = st.text_area("🌱 ¿Qué funcionó?")
        f2 = st.text_area("🍂 ¿Qué sobró?")
        animo = st.slider("¿Cómo te sientes?", 1, 5, 3)
        if st.form_submit_button("Cerrar semana 🌙"):
            ejecutar("INSERT INTO revisiones (fecha, funciono, sobro, animo, creado) VALUES (?,?,?,?,?)", (hoy.isoformat(), f1, f2, animo, hoy.isoformat()))
            st.success("Semana cerrada.")

# 6. Barra de Navegación Inferior (6 botones en formato app)
st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    if st.button("🌞\nHoy", use_container_width=True, type="primary" if st.session_state.pagina=="hoy" else "secondary"): st.session_state.pagina = "hoy"; st.rerun()
with c2:
    if st.button("✍️\nCapturar", use_container_width=True, type="primary" if st.session_state.pagina=="capturar" else "secondary"): st.session_state.pagina = "capturar"; st.rerun()
with c3:
    if st.button("🧩\nÁreas", use_container_width=True, type="primary" if st.session_state.pagina=="areas" else "secondary"): st.session_state.pagina = "areas"; st.rerun()
with c4:
    if st.button("📁\nProyectos", use_container_width=True, type="primary" if st.session_state.pagina=="proyectos" else "secondary"): st.session_state.pagina = "proyectos"; st.rerun()
with c5:
    if st.button("🗓️\nPlan", use_container_width=True, type="primary" if st.session_state.pagina=="plan" else "secondary"): st.session_state.pagina = "plan"; st.rerun()
with c6:
    if st.button("🔄\nRevisión", use_container_width=True, type="primary" if st.session_state.pagina=="revision" else "secondary"): st.session_state.pagina = "revision"; st.rerun()
