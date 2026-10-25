import streamlit as st
import sqlite3
import json
from datetime import date, timedelta

# 1. Configuración de página
st.set_page_config(page_title="Mi Semana", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")

# 2. CSS con diseño llamativo y acogedor (Pastel + Zen)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #F8F4E6; } /* Fondo crema suave */
    .block-container { padding-top: 1.5rem; padding-bottom: 6rem; max-width: 600px; }
    
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&family=Playfair+Display:ital@1&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }

    /* Encabezado con degradado pastel */
    .hero {
        background: linear-gradient(135deg, #A8D5BA, #C3B1E1);
        padding: 24px; border-radius: 30px; color: #2D3142;
        text-align: center; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(168, 213, 186, 0.3);
    }
    .hero h1 { margin: 0; font-size: 28px; font-weight: 700; }
    .hero p { margin: 5px 0 0 0; font-size: 14px; font-style: italic; font-family: 'Playfair Display', serif; }

    /* Tarjetas */
    .card {
        background: white; border-radius: 24px; padding: 18px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.04); border: 1px solid #F0EAD6; margin-bottom: 15px;
    }
    
    /* Botones de Navegación Inferior */
    div.stButton > button {
        background-color: white; color: #7A8B8B; border: 1px solid #E6E0D4;
        border-radius: 20px; padding: 10px 2px; width: 100%; font-weight: 600; font-size: 12px;
        transition: all 0.3s ease;
    }
    div.stButton > button[kind="primary"] { 
        background-color: #A8D5BA; color: #2D3142; border: none; box-shadow: 0 4px 12px rgba(168, 213, 186, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# 3. Base de Datos (Lógica completa)
DB = "mi_semana.db"
def get_conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT);
        CREATE TABLE IF NOT EXISTS areas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, emoji TEXT, meta TEXT, activa INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, tipo TEXT, area_id INTEGER, fecha TEXT, duracion_min INTEGER DEFAULT 30, energia TEXT, prioridad INTEGER DEFAULT 0, estado TEXT DEFAULT 'pendiente');
        CREATE TABLE IF NOT EXISTS revisiones (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, funciono TEXT, sobro TEXT, animo INTEGER);
    """)
    c.commit()
    if not c.execute("SELECT * FROM areas").fetchone():
        areas_def = [("Trabajo", "💼"), ("Hogar", "🏠"), ("Familia", "👨‍👩‍👧"), ("Pareja", "💞"), ("Salud", "🩺"), ("Hobbies", "🎨"), ("Aprendizaje", "📚"), ("Descanso", "🌙")]
        c.executemany("INSERT INTO areas (nombre, emoji) VALUES (?,?)", areas_def)
        c.commit()
    c.close()

def cfg_get(k, default=None):
    row = get_conn().execute("SELECT valor FROM config WHERE clave=?", (k,)).fetchone()
    return json.loads(row["valor"]) if row else default

def cfg_set(k, v):
    c = get_conn()
    c.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES (?,?)", (k, json.dumps(v)))
    c.commit(); c.close()

def areas():
    return get_conn().execute("SELECT * FROM areas WHERE activa=1").fetchall()

def ejecutar(sql, params=()):
    c = get_conn()
    c.execute(sql, params)
    c.commit(); c.close()

init_db()

# 4. Onboarding
if not cfg_get("onboarding"):
    st.markdown("<div class='hero'><h1>🌿 Mi Semana</h1><p>Tu vida entera, no solo tu trabajo.</p></div>", unsafe_allow_html=True)
    with st.form("onb"):
        nombre = st.text_input("¿Cómo te llamas?", placeholder="Ej: Camila")
        ciudad = st.text_input("¿Dónde vives?", value="Santander de Quilichao")
        if st.form_submit_button("Empezar 🌱"):
            cfg_set("nombre", nombre.strip() or "Vecino")
            cfg_set("ciudad", ciudad.strip())
            cfg_set("onboarding", True)
            st.rerun()
    st.stop()

# 5. Estado y navegación
if "pagina" not in st.session_state: st.session_state.pagina = "hoy"
nombre = cfg_get("nombre")
hoy = date.today()
hoy_str = hoy.isoformat()

# --- VISTA: HOY ---
if st.session_state.pagina == "hoy":
    st.markdown(f"<div class='hero'><h1>Hola, {nombre} 👋</h1><p>{hoy.strftime('%A, %d de %B')}</p></div>", unsafe_allow_html=True)
    
    with st.form("captura_rapida", clear_on_submit=True):
        texto = st.text_input("Captura rápida", placeholder="Escribe algo y presiona Enter…", label_visibility="collapsed")
        if st.form_submit_button("Guardar en bandeja ✨"):
            if texto:
                ejecutar("INSERT INTO items (titulo, fecha) VALUES (?,?)", (texto, hoy_str))
                st.rerun()

    st.markdown("### 🎯 Mis 3 prioridades de hoy")
    prios = get_conn().execute("SELECT * FROM items WHERE estado='pendiente' AND fecha=? AND prioridad>0 ORDER BY prioridad", (hoy_str,)).fetchall()
    
    if not prios:
        st.info("Aún no eliges. Máximo 3: lo demás puede esperar.")
    for p in prios:
        area = get_conn().execute("SELECT emoji FROM areas WHERE id=?", (p["area_id"],)).fetchone()
        emoji = area["emoji"] if area else "🌱"
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        c1.markdown(f"**{p['prioridad']}.** {emoji} {p['titulo']}  \n<span style='font-size:12px; color:#888;'>{p['duracion_min']} min · {p['energia']}</span>", unsafe_allow_html=True)
        if c2.button("✔", key=f"hecho_{p['id']}"):
            ejecutar("UPDATE items SET estado='hecho' WHERE id=?", (p["id"],))
            st.rerun()
        if c3.button("⏭", key=f"rep_{p['id']}"):
            manana = (hoy + timedelta(days=1)).isoformat()
            ejecutar("UPDATE items SET fecha=?, prioridad=0 WHERE id=?", (manana, p["id"]))
            st.rerun()

    with st.expander("➕ Elegir prioridades de hoy"):
        opciones = get_conn().execute("SELECT id, titulo FROM items WHERE estado='pendiente' AND (fecha IS NULL OR fecha<=?)", (hoy_str,)).fetchall()
        labels = {r["id"]: r["titulo"] for r in opciones}
        sel = st.multiselect("Máximo 3.", list(labels.keys()), format_func=lambda i: labels[i], max_selections=3)
        if st.button("Fijar prioridades"):
            for n, item_id in enumerate(sel, 1):
                ejecutar("UPDATE items SET fecha=?, prioridad=? WHERE id=?", (hoy_str, n, item_id))
            st.rerun()

# --- VISTA: CAPTURAR ---
elif st.session_state.pagina == "capturar":
    st.markdown("<div class='hero'><h1>✍️ Capturar</h1><p>Saca todo de la cabeza</p></div>", unsafe_allow_html=True)
    with st.form("nuevo", clear_on_submit=True):
        titulo = st.text_input("¿Qué es?")
        tipo = st.selectbox("Tipo", ["tarea", "compromiso", "rutina"])
        dur = st.number_input("Duración (min)", 5, 480, 30, 5)
        if st.form_submit_button("Guardar 🌿"):
            if titulo:
                ejecutar("INSERT INTO items (titulo, tipo, fecha, duracion_min) VALUES (?,?,?,?)", (titulo, tipo, hoy_str, dur))
                st.success("Guardado")
                st.rerun()

    st.markdown("### 📥 Bandeja de entrada")
    bandeja = get_conn().execute("SELECT * FROM items WHERE estado='pendiente' AND (fecha IS NULL OR fecha='')").fetchall()
    if not bandeja: st.caption("Vacía. Respira 😌")
    for b in bandeja:
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        c1.write(f"• {b['titulo']}")
        if c2.button("Hoy", key=f"bh_{b['id']}"):
            ejecutar("UPDATE items SET fecha=? WHERE id=?", (hoy_str, b["id"]))
            st.rerun()
        if c3.button("🗑", key=f"bd_{b['id']}"):
            ejecutar("UPDATE items SET estado='archivado' WHERE id=?", (b["id"],))
            st.rerun()

# --- VISTA: ÁREAS ---
elif st.session_state.pagina == "areas":
    st.markdown("<div class='hero'><h1>🧩 Áreas</h1><p>Las partes de tu vida</p></div>", unsafe_allow_html=True)
    for a in areas():
        pend = get_conn().execute("SELECT COUNT(*) c FROM items WHERE estado='pendiente' AND area_id=?", (a["id"],)).fetchone()["c"]
        with st.expander(f"{a['emoji']} {a['nombre']} · {pend} pendientes"):
            meta = st.text_input("¿Qué quieres cuidar aquí?", value=a["meta"] or "", key=f"meta_{a['id']}")
            if st.button("Guardar", key=f"gm_{a['id']}"):
                ejecutar("UPDATE areas SET meta=? WHERE id=?", (meta, a["id"]))
                st.toast("Listo 🌿")

# --- VISTA: PROYECTOS ---
elif st.session_state.pagina == "proyectos":
    st.markdown("<div class='hero'><h1>📁 Proyectos</h1><p>Cosas grandes que toman más de un día</p></div>", unsafe_allow_html=True)
    st.info("Próximamente: gestión de proyectos y tareas vinculadas.")

# --- VISTA: PLAN ---
elif st.session_state.pagina == "plan":
    st.markdown("<div class='hero'><h1>🗓️ Plan Semanal</h1><p>Decide antes de que empiece</p></div>", unsafe_allow_html=True)
    
    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)
    st.caption(f"Semana del {inicio.strftime('%d/%m')} al {fin.strftime('%d/%m')}")
    
    total_cap = get_conn().execute("SELECT SUM(duracion_min) s FROM items WHERE estado='pendiente' AND fecha BETWEEN ? AND ?", (inicio.isoformat(), fin.isoformat())).fetchone()["s"] or 0
    st.progress(min(total_cap / (35 * 60), 1.0))
    st.markdown(f"**{total_cap/60:.1f} h** comprometidas de **35 h** reales.")
    if total_cap / (35 * 60) > 0.85:
        st.warning("⚠️ Semana justa. Evita agregar cosas nuevas.")
    else:
        st.success("✅ Semana humanamente posible.")

# --- VISTA: REVISIÓN ---
elif st.session_state.pagina == "revision":
    st.markdown("<div class='hero'><h1>🔄 Revisión</h1><p>Cierra sin juicio. Solo información.</p></div>", unsafe_allow_html=True)
    with st.form("rev", clear_on_submit=True):
        funciono = st.text_area("🌱 ¿Qué funcionó?")
        sobro = st.text_area("🍂 ¿Qué sobró?")
        animo = st.slider("¿Cómo te sientes?", 1, 5, 3)
        if st.form_submit_button("Cerrar semana 🌙"):
            ejecutar("INSERT INTO revisiones (fecha, funciono, sobro, animo) VALUES (?,?,?,?)", (hoy_str, funciono, sobro, animo))
            st.success("Semana cerrada.")

# 6. Barra de Navegación Inferior
st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if st.button("🌞 Hoy", use_container_width=True, type="primary" if st.session_state.pagina=="hoy" else "secondary"):
        st.session_state.pagina = "hoy"; st.rerun()
with c2:
    if st.button("✍️ Capturar", use_container_width=True, type="primary" if st.session_state.pagina=="capturar" else "secondary"):
        st.session_state.pagina = "capturar"; st.rerun()
with c3:
    if st.button("🧩 Áreas", use_container_width=True, type="primary" if st.session_state.pagina=="areas" else "secondary"):
        st.session_state.pagina = "areas"; st.rerun()
with c4:
    if st.button("🗓️ Plan", use_container_width=True, type="primary" if st.session_state.pagina=="plan" else "secondary"):
        st.session_state.pagina = "plan"; st.rerun()
with c5:
    if st.button("🔄 Revisión", use_container_width=True, type="primary" if st.session_state.pagina=="revision" else "secondary"):
        st.session_state.pagina = "revision"; st.rerun()
