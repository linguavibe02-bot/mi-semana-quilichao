import streamlit as st
import sqlite3
import json
from datetime import date, timedelta

# 1. Configuración Mobile-First
st.set_page_config(page_title="Mi Semana", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")

# 2. CSS de App (Paleta Zen original)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #FBF7F0; }
    .block-container { padding-top: 2rem; padding-bottom: 6rem; max-width: 600px; }
    
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&family=Nunito:wght@400;600;700&display=swap');
    h1, h2, h3 { font-family: 'Lora', serif; color: #123B33; }
    p, div, input { font-family: 'Nunito', sans-serif; }

    .hero {
        background: linear-gradient(135deg, #1F6F5C, #2E8B74);
        padding: 20px; border-radius: 20px; color: white;
        text-align: center; margin-bottom: 20px; box-shadow: 0 8px 20px rgba(31,111,92,0.2);
    }
    .hero h1 { margin: 0; font-size: 24px; color: white; }
    .hero p { margin: 5px 0 0 0; font-size: 13px; opacity: 0.9; }

    .card {
        background: white; border-radius: 16px; padding: 18px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #EFE7DA; margin-bottom: 15px;
    }
    
    /* Botones navegación */
    div.stButton > button {
        background-color: white; color: #1F6F5C; border: 1px solid #E4D9C6;
        border-radius: 12px; padding: 8px 2px; width: 100%; font-weight: 700; font-size: 12px;
    }
    div.stButton > button[kind="primary"] { background-color: #1F6F5C; color: white; border: none; }
</style>
""", unsafe_allow_html=True)

# 3. Base de Datos (Lógica intacta)
DB = "mi_semana.db"
def get_conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_conn()
    c.execute("CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS areas (id INTEGER PRIMARY KEY, nombre TEXT, emoji TEXT, meta TEXT, activa INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, titulo TEXT, tipo TEXT, area_id INTEGER, fecha TEXT, estado TEXT DEFAULT 'pendiente')")
    c.commit(); c.close()
    
    if not get_conn().execute("SELECT * FROM areas").fetchone():
        areas_def = [("Trabajo", "💼"), ("Hogar", "🏠"), ("Salud", "🩺"), ("Descanso", "🌙")]
        c = get_conn()
        for a in areas_def: c.execute("INSERT INTO areas (nombre, emoji) VALUES (?,?)", a)
        c.commit(); c.close()

def cfg_get(k, default=None):
    row = get_conn().execute("SELECT valor FROM config WHERE clave=?", (k,)).fetchone()
    return json.loads(row["valor"]) if row else default

def cfg_set(k, v):
    c = get_conn()
    c.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES (?,?)", (k, json.dumps(v)))
    c.commit(); c.close()

init_db()

if "pagina" not in st.session_state: st.session_state.pagina = "hoy"

# 4. Onboarding (Si no hay nombre)
if not cfg_get("nombre"):
    st.markdown("<div class='hero'><h1>🌿 Mi Semana</h1><p>Tu vida entera en una semana realista</p></div>", unsafe_allow_html=True)
    with st.form("onb"):
        nombre = st.text_input("¿Cómo te llamas?")
        if st.form_submit_button("Empezar"):
            cfg_set("nombre", nombre); st.rerun()
    st.stop()

# 5. Vistas
nombre = cfg_get("nombre")
hoy = date.today()

if st.session_state.pagina == "hoy":
    st.markdown(f"<div class='hero'><h1>Hola, {nombre} 👋</h1><p>Hoy es un buen día</p></div>", unsafe_allow_html=True)
    
    with st.form("captura", clear_on_submit=True):
        texto = st.text_input("Captura rápida", placeholder="¿Qué tienes en mente?")
        if st.form_submit_button("Guardar ✨"):
            if texto:
                c = get_conn(); c.execute("INSERT INTO items (titulo, fecha) VALUES (?,?)", (texto, hoy.isoformat())); c.commit(); c.close()
                st.rerun()

    st.markdown("### 🎯 Prioridades de hoy")
    c = get_conn()
    pendientes = c.execute("SELECT * FROM items WHERE estado='pendiente' AND fecha=?", (hoy.isoformat(),)).fetchall()
    c.close()
    
    if not pendientes: st.info("No tienes pendientes para hoy. Respira 😌")
    for p in pendientes:
        st.markdown(f"<div class='card'><b>{p['titulo']}</b></div>", unsafe_allow_html=True)

elif st.session_state.pagina == "capturar":
    st.markdown("<div class='hero'><h1>✍️ Capturar</h1><p>Saca todo de tu cabeza</p></div>", unsafe_allow_html=True)
    with st.form("form_captura", clear_on_submit=True):
        t = st.text_input("¿Qué es?")
        f = st.date_input("¿Para cuándo?")
        if st.form_submit_button("Guardar 🌿"):
            if t:
                c = get_conn(); c.execute("INSERT INTO items (titulo, fecha) VALUES (?,?)", (t, f.isoformat())); c.commit(); c.close()
                st.success("Guardado")

elif st.session_state.pagina == "areas":
    st.markdown("<div class='hero'><h1>🧩 Áreas</h1><p>Las partes de tu vida</p></div>", unsafe_allow_html=True)
    c = get_conn()
    for a in c.execute("SELECT * FROM areas").fetchall():
        st.markdown(f"<div class='card'><b>{a['emoji']} {a['nombre']}</b></div>", unsafe_allow_html=True)
    c.close()

elif st.session_state.pagina == "plan":
    st.markdown("<div class='hero'><h1>🗓️ Plan</h1><p>Decide antes de que empiece</p></div>", unsafe_allow_html=True)
    st.info("Configuración de capacidad semanal (Próximamente en detalle)")

elif st.session_state.pagina == "revision":
    st.markdown("<div class='hero'><h1>🔄 Revisión</h1><p>Cierra la semana sin culpa</p></div>", unsafe_allow_html=True)
    with st.form("rev"):
        st.text_area("¿Qué funcionó?")
        st.text_area("¿Qué sobró?")
        if st.form_submit_button("Cerrar semana"):
            st.success("Semana cerrada. Lo que no hiciste también es información.")

# 6. Barra de Navegación Inferior (5 íconos)
st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if st.button("🌞 Hoy", use_container_width=True, type="primary" if st.session_state.pagina=="hoy" else "secondary"):
        st.session_state.pagina = "hoy"; st.rerun()
with c2:
    if st.button("✍️ Nota", use_container_width=True, type="primary" if st.session_state.pagina=="capturar" else "secondary"):
        st.session_state.pagina = "capturar"; st.rerun()
with c3:
    if st.button("🧩 Áreas", use_container_width=True, type="primary" if st.session_state.pagina=="areas" else "secondary"):
        st.session_state.pagina = "areas"; st.rerun()
with c4:
    if st.button("🗓️ Plan", use_container_width=True, type="primary" if st.session_state.pagina=="plan" else "secondary"):
        st.session_state.pagina = "plan"; st.rerun()
with c5:
    if st.button("🔄 Cierre", use_container_width=True, type="primary" if st.session_state.pagina=="revision" else "secondary"):
        st.session_state.pagina = "revision"; st.rerun()
