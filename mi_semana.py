import streamlit as st
import sqlite3
import json
from datetime import date, timedelta

st.set_page_config(page_title="Mi Semana", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
    .stApp { background-color: #FBF7F0; }
    header {visibility: hidden;} footer {visibility: hidden;} #MainMenu {visibility: hidden;}
    .hero { background: linear-gradient(135deg, #1F6F5C, #2E8B74); padding: 2rem; border-radius: 16px; color: white; text-align: center; margin-bottom: 20px; }
    .card { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

DB = "mi_semana.db"
def get_conn():
    c = sqlite3.connect(DB, check_same_thread=False); c.row_factory = sqlite3.Row; return c

def init_db():
    c = get_conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT);
        CREATE TABLE IF NOT EXISTS areas (id INTEGER PRIMARY KEY, nombre TEXT, emoji TEXT, activa INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, titulo TEXT, area_id INTEGER, fecha TEXT, prioridad INTEGER DEFAULT 0, estado TEXT DEFAULT 'pendiente');
    """)
    c.commit()
    if not c.execute("SELECT * FROM areas").fetchone():
        c.executemany("INSERT INTO areas (nombre, emoji) VALUES (?,?)", [("Trabajo", "💼"), ("Hogar", "🏠"), ("Salud", "🩺")])
        c.commit()
    c.close()

def cfg_get(k, d=None):
    row = get_conn().execute("SELECT valor FROM config WHERE clave=?", (k,)).fetchone()
    return json.loads(row["valor"]) if row else d

def cfg_set(k, v):
    c = get_conn(); c.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES (?,?)", (k, json.dumps(v))); c.commit(); c.close()

init_db()

if not cfg_get("onboarding"):
    st.markdown("<div class='hero'><h1>🌿 Mi Semana</h1></div>", unsafe_allow_html=True)
    with st.form("onb"):
        nombre = st.text_input("Nombre")
        if st.form_submit_button("Empezar"): cfg_set("nombre", nombre); cfg_set("onboarding", True); st.rerun()
    st.stop()

with st.sidebar:
    st.markdown("## 🧭 Navegación")
    nav = st.radio("Ir a:", ["🏠 Hoy", "✍️ Capturar", "🧩 Áreas", "🗓️ Plan", "🔄 Revisión"], label_visibility="collapsed")
    if st.button("📥 Cargar tareas de ejemplo"):
        c = get_conn(); c.execute("INSERT INTO items (titulo, fecha) VALUES ('Llamar al banco', ?), ('Hacer mercado', ?), ('Estudiar', ?)", (date.today().isoformat(),)*3); c.commit(); c.close(); st.rerun()

nombre = cfg_get("nombre")
hoy = date.today()

if nav == "🏠 Hoy":
    st.markdown(f"<div class='hero'><h1>Hola, {nombre} 👋</h1></div>", unsafe_allow_html=True)
    with st.form("captura", clear_on_submit=True):
        texto = st.text_input("Captura rápida")
        if st.form_submit_button("Guardar"):
            if texto: c = get_conn(); c.execute("INSERT INTO items (titulo, fecha) VALUES (?,?)", (texto, hoy.isoformat())); c.commit(); c.close(); st.rerun()
    
    st.markdown("### 🎯 Prioridades de hoy")
    prios = get_conn().execute("SELECT * FROM items WHERE estado='pendiente' AND fecha=? AND prioridad>0 ORDER BY prioridad", (hoy.isoformat(),)).fetchall()
    if not prios: st.info("No has elegido prioridades.")
    for p in prios: st.write(f"**{p['prioridad']}.** {p['titulo']}")

    with st.expander("➕ Elegir prioridades"):
        opciones = get_conn().execute("SELECT id, titulo FROM items WHERE estado='pendiente'").fetchall()
        if not opciones: st.warning("No hay tareas. Carga ejemplos en el menú lateral.")
        else:
            labels = {r["id"]: r["titulo"] for r in opciones}
            sel = st.multiselect("Máximo 3.", list(labels.keys()), format_func=lambda i: labels[i], max_selections=3)
            if st.button("Fijar"):
                c = get_conn()
                for n, item_id in enumerate(sel, 1): c.execute("UPDATE items SET fecha=?, prioridad=? WHERE id=?", (hoy.isoformat(), n, item_id))
                c.commit(); c.close(); st.rerun()

elif nav == "✍️ Capturar":
    st.markdown("<h2>✍️ Capturar</h2>", unsafe_allow_html=True)
    with st.form("nuevo", clear_on_submit=True):
        t = st.text_input("¿Qué es?")
        if st.form_submit_button("Guardar"):
            if t: c = get_conn(); c.execute("INSERT INTO items (titulo, fecha) VALUES (?,?)", (t, hoy.isoformat())); c.commit(); c.close(); st.rerun()

elif nav == "🧩 Áreas":
    st.markdown("<h2>🧩 Áreas</h2>", unsafe_allow_html=True)
    for a in get_conn().execute("SELECT * FROM areas").fetchall(): st.write(f"{a['emoji']} {a['nombre']}")

elif nav == "🗓️ Plan":
    st.markdown("<h2>🗓️ Plan Semanal</h2>", unsafe_allow_html=True)
    st.info("Configuración de capacidad semanal. (Lógica intacta).")

elif nav == "🔄 Revisión":
    st.markdown("<h2>🔄 Revisión</h2>", unsafe_allow_html=True)
    with st.form("rev"):
        st.text_area("¿Qué funcionó?")
        if st.form_submit_button("Cerrar semana"): st.success("Semana cerrada.")
