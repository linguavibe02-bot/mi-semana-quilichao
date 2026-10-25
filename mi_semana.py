# -*- coding: utf-8 -*-
"""
MI SEMANA — "Tu vida entera en una semana realista"
Fase 1 · Prototipo funcional (Streamlit + SQLite)
Ejecutar:  streamlit run mi_semana.py
Requisito: pip install streamlit
"""

import json
import sqlite3
from datetime import date, timedelta

import streamlit as st

DB = "mi_semana.db"

st.set_page_config(
    page_title="Mi Semana · Quilichao",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- ESTILOS
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
.stApp { background: #FBF7F0; }
section[data-testid="stSidebar"] { background: #123B33; }
section[data-testid="stSidebar"] * { color: #F3EFE6 !important; }
.block-container { padding-top: 1.2rem; max-width: 1100px; }
.hero {
  display:flex; gap:16px; align-items:center;
  background: linear-gradient(120deg,#1F6F5C,#2E8B74 60%,#E4A11B 165%);
  padding:20px 24px; border-radius:20px; color:#fff; margin-bottom:18px;
  box-shadow:0 10px 26px rgba(31,111,92,.22);
}
.hero-emoji { font-size:38px; }
.hero-title { font-size:26px; font-weight:800; line-height:1.1; }
.hero-sub { font-size:14px; opacity:.92; }
.card {
  background:#fff; border-radius:16px; padding:16px 18px;
  box-shadow:0 4px 14px rgba(0,0,0,.05); border:1px solid #EFE7DA;
}
.card-num { font-size:26px; font-weight:800; color:#1F6F5C; }
.card-lbl { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#8A8071; }
.card-pie { font-size:13px; color:#5C564C; margin-top:4px; }
.stButton>button {
  border-radius:12px; border:1px solid #E4D9C6; background:#fff;
  color:#1F6F5C; font-weight:700;
}
.stButton>button:hover { background:#1F6F5C; color:#fff; border-color:#1F6F5C; }
div[data-testid="stForm"] {
  background:#fff; border-radius:16px; padding:14px 16px; border:1px solid #EFE7DA;
}
h3 { color:#123B33; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------- BASE DE DATOS
AREAS_DEFECTO = [
    ("Trabajo", "💼"),
    ("Hogar", "🏠"),
    ("Familia", "👨‍👩‍👧"),
    ("Pareja", "💞"),
    ("Salud", "🩺"),
    ("Hobbies", "🎨"),
    ("Aprendizaje", "📚"),
    ("Descanso", "🌙"),
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT UNIQUE NOT NULL,
  emoji TEXT DEFAULT '🌱',
  meta TEXT DEFAULT '',
  activa INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS proyectos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  area_id INTEGER,
  nombre TEXT NOT NULL,
  nota TEXT DEFAULT '',
  estado TEXT DEFAULT 'activo',
  creado TEXT
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  tipo TEXT DEFAULT 'tarea',
  area_id INTEGER,
  proyecto_id INTEGER,
  fecha TEXT,
  duracion_min INTEGER DEFAULT 30,
  energia TEXT DEFAULT 'Media',
  prioridad INTEGER DEFAULT 0,
  estado TEXT DEFAULT 'pendiente',
  creado TEXT
);
CREATE TABLE IF NOT EXISTS semanas (
  inicio TEXT PRIMARY KEY,
  capacidad TEXT DEFAULT '{}',
  prioridades TEXT DEFAULT '[]',
  nota TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS revisiones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha TEXT, funciono TEXT, sobro TEXT, abandono TEXT, animo INTEGER, creado TEXT
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
        "INSERT INTO config(clave,valor) VALUES(?,?) "
        "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, json.dumps(valor, ensure_ascii=False)),
    )


def areas():
    return consultar("SELECT * FROM areas WHERE activa=1 ORDER BY id")


# ---------------------------------------------------------------- FECHAS
def lunes(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def fecha_es(d):
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    meses = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dias[d.weekday()]} {d.day} {meses[d.month - 1]}"


def capacidad_semana(inicio):
    row = consultar("SELECT capacidad FROM semanas WHERE inicio=?", (inicio,))
    if not row:
        return {}
    crudo = json.loads(row[0]["capacidad"] or "{}")
    return {int(k): v for k, v in crudo.items()}


def carga_semana(inicio, fin):
    rows = consultar(
        "SELECT area_id, COALESCE(SUM(duracion_min),0) m FROM items "
        "WHERE estado='pendiente' AND fecha BETWEEN ? AND ? GROUP BY area_id",
        (inicio, fin),
    )
    return {r["area_id"]: r["m"] for r in rows}


def guardar_semana(inicio, capacidad=None, prioridades=None, nota=None):
    row = consultar("SELECT * FROM semanas WHERE inicio=?", (inicio,))
    actual = dict(row[0]) if row else {
        "inicio": inicio, "capacidad": "{}", "prioridades": "[]", "nota": ""
    }
    if capacidad is not None:
        actual["capacidad"] = json.dumps(capacidad)
    if prioridades is not None:
        actual["prioridades"] = json.dumps(prioridades)
    if nota is not None:
        actual["nota"] = nota
    ejecutar(
        "INSERT OR REPLACE INTO semanas (inicio, capacidad, prioridades, nota) "
        "VALUES (?,?,?,?)",
        (inicio, actual["capacidad"], actual["prioridades"], actual["nota"]),
    )


# ---------------------------------------------------------------- UI BASE
def hero(titulo, subtitulo, emoji="🌿"):
    st.markdown(
        f'<div class="hero"><div class="hero-emoji">{emoji}</div>'
        f'<div><div class="hero-title">{titulo}</div>'
        f'<div class="hero-sub">{subtitulo}</div></div></div>',
        unsafe_allow_html=True,
    )


def tarjeta(col, etiqueta, valor, pie=""):
    col.markdown(
        f'<div class="card"><div class="card-lbl">{etiqueta}</div>'
        f'<div class="card-num">{valor}</div>'
        f'<div class="card-pie">{pie}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- ONBOARDING
def onboarding():
    hero(
        "Mi Semana",
        "Tu vida entera en una semana realista. Sin culpa, sin listas infinitas.",
        "🌿",
    )
    st.markdown("#### Cuéntame lo mínimo para empezar")
    with st.form("onb"):
        nombre = st.text_input("¿Cómo te llamas?", placeholder="Ej: Camila")
        ciudad = st.text_input("¿Dónde vives?", value="Santander de Quilichao")
        horas = st.slider(
            "¿Cuántas horas reales tienes esta semana para tus cosas (sin contar el trabajo)?",
            5, 80, 35, 5,
        )
        ok = st.form_submit_button("Empezar 🌱")
    if ok:
        cfg_set("nombre", nombre.strip() or "Vecino")
        cfg_set("ciudad", ciudad.strip() or "Santander de Quilichao")
        cfg_set("capacidad_default", horas)
        cfg_set("onboarding", True)
        st.rerun()


# ---------------------------------------------------------------- PÁGINA: HOY
def pagina_hoy():
    nombre = cfg_get("nombre", "Vecino")
    hoy = date.today()
    inicio = lunes(hoy)
    fin = inicio + timedelta(days=6)
    hero(
        f"Hola, {nombre} 👋",
        f"{fecha_es(hoy).capitalize()} · {cfg_get('ciudad', 'Santander de Quilichao')}",
        "🌿",
    )

    with st.form("captura_rapida", clear_on_submit=True):
        texto = st.text_input(
            "Captura rápida",
            placeholder="Escribe algo que tengas en la cabeza y presiona Enter…",
            label_visibility="collapsed",
        )
        guardar = st.form_submit_button("Guardar en bandeja ✨")
    if guardar and texto.strip():
        ejecutar(
            "INSERT INTO items (titulo, tipo, creado) VALUES (?,?,?)",
            (texto.strip(), "tarea", hoy.isoformat()),
        )
        st.toast("Guardado. Ya no está en tu cabeza 🌿")
        st.rerun()

    pendientes = consultar(
        "SELECT COUNT(*) c FROM items WHERE estado='pendiente'"
    )[0]["c"]
    prios = consultar(
        "SELECT * FROM items WHERE estado='pendiente' AND fecha=? AND prioridad>0 "
        "ORDER BY prioridad",
        (hoy.isoformat(),),
    )
    cap = capacidad_semana(inicio.isoformat())
    total_cap_min = sum(cap.values()) * 60
    carga = sum(carga_semana(inicio.isoformat(), fin.isoformat()).values())

    c1, c2, c3 = st.columns(3)
    tarjeta(c1, "Pendientes", pendientes, "en todas tus áreas")
    if total_cap_min:
        tarjeta(c2, "Semana usada", f"{carga / total_cap_min * 100:.0f}%",
                f"{carga/60:.1f} h de {total_cap_min/60:.0f} h reales")
    else:
        tarjeta(c2, "Semana usada", "—", "configura tu capacidad")
    tarjeta(c3, "Prioridades hoy", f"{len(prios)}/3", "lo demás puede esperar")

    st.markdown("### 🎯 Mis 3 prioridades de hoy")
    if not prios:
        st.info("Aún no eliges. Máximo 3: el resto no desaparece, solo espera.")
    for p in prios:
        fila = consultar("SELECT emoji FROM areas WHERE id=?", (p["area_id"],))
        emoji = fila[0]["emoji"] if fila else "🌱"
        a, b, c = st.columns([0.62, 0.19, 0.19])
        a.markdown(
            f"**{p['prioridad']}.** {emoji} {p['titulo']}  \n"
            f"<span style='color:#8A8071;font-size:13px'>"
            f"{p['duracion_min']} min · energía {p['energia']}</span>",
            unsafe_allow_html=True,
        )
        if b.button("✔ Hecho", key=f"hecho_{p['id']}"):
            ejecutar("UPDATE items SET estado='hecho' WHERE id=?", (p["id"],))
            st.rerun()
        if c.button("⏭ Mañana", key=f"rep_{p['id']}"):
            manana = (hoy + timedelta(days=1)).isoformat()
            ejecutar(
                "UPDATE items SET fecha=?, prioridad=0 WHERE id=?",
                (manana, p["id"]),
            )
            st.toast("Reprogramar no es fallar. Mañana será posible 🌿")
            st.rerun()

    with st.expander("➕ Elegir o cambiar prioridades de hoy", expanded=not prios):
        opciones = consultar(
            "SELECT id, titulo FROM items WHERE estado='pendiente' "
            "AND (fecha IS NULL OR fecha<=?) ORDER BY creado DESC LIMIT 100",
            (hoy.isoformat(),),
        )
        labels = {r["id"]: r["titulo"] for r in opciones}
        actuales = [p["id"] for p in prios]
        sel = st.multiselect(
            "Máximo 3. Lo demás puede esperar.",
            list(labels.keys()),
            default=[i for i in actuales if i in labels],
            format_func=lambda i: labels[i],
            max_selections=3,
        )
        if st.button("Fijar prioridades"):
            ejecutar("UPDATE items SET prioridad=0 WHERE fecha=?", (hoy.isoformat(),))
            for n, item_id in enumerate(sel, start=1):
                ejecutar(
                    "UPDATE items SET fecha=?, prioridad=? WHERE id=?",
                    (hoy.isoformat(), n, item_id),
                )
            st.rerun()

    st.markdown("### 📌 Compromisos fijos de hoy")
    comp = consultar(
        "SELECT * FROM items WHERE estado='pendiente' AND tipo='compromiso' AND fecha=?",
        (hoy.isoformat(),),
    )
    if not comp:
        st.caption("Sin compromisos fijos. Día flexible 😌")
    for c in comp:
        a, b = st.columns([0.82, 0.18])
        a.write(f"• **{c['titulo']}**")
        if b.button("✔", key=f"ch_{c['id']}"):
            ejecutar("UPDATE items SET estado='hecho' WHERE id=?", (c["id"],))
            st.rerun()

    st.markdown("### 🧮 ¿Tu semana es humanamente posible?")
    if total_cap_min == 0:
        st.info(
            "Aún no configuras tu capacidad. Ve a **Plan semanal** y dime "
            "cuántas horas reales tienes."
        )
    else:
        pct = carga / total_cap_min
        st.progress(min(pct, 1.0))
        if pct <= 0.85:
            estado = "✅ Va bien, hay aire"
        elif pct <= 1.0:
            estado = "⚠️ Justa, cuidado con agregar más"
        else:
            estado = "🚨 Sobrecargada: algo tiene que salir"
        st.caption(
            f"{carga/60:.1f} h comprometidas de {total_cap_min/60:.0f} h reales · {estado}"
        )


# ---------------------------------------------------------------- PÁGINA: CAPTURAR
def pagina_capturar():
    hero("Capturar", "Saca todo de la cabeza. Ya decidirás después.", "✍️")
    lista_areas = areas()
    etiquetas = [f"{a['emoji']} {a['nombre']}" for a in lista_areas]
    mapa = {et: a["id"] for et, a in zip(etiquetas, lista_areas)}

    with st.form("nuevo_item", clear_on_submit=True):
        titulo = st.text_input("¿Qué es?")
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", ["tarea", "compromiso", "rutina", "nota"])
        area_et = c2.selectbox("Área de vida", etiquetas)
        c3, c4 = st.columns(2)
        fecha = c3.date_input("¿Para cuándo?", value=date.today())
        dur = c4.number_input("Duración estimada (min)", 5, 480, 30, 5)
        energia = st.select_slider("Energía que pide", ["Baja", "Media", "Alta"], value="Media")
        nota = st.text_area("Nota (opcional)", height=70)
        ok = st.form_submit_button("Guardar 🌿")
    if ok and titulo.strip():
        ejecutar(
            "INSERT INTO items (titulo, tipo, area_id, fecha, duracion_min, energia, creado) "
            "VALUES (?,?,?,?,?,?,?)",
            (titulo.strip(), tipo, mapa[area_et], fecha.isoformat(), int(dur), energia,
             date.today().isoformat()),
        )
        st.success("Guardado ✅")
        st.rerun()

    st.markdown("### 📥 Bandeja de entrada")
    bandeja = consultar(
        "SELECT * FROM items WHERE estado='pendiente' AND (fecha IS NULL OR fecha='') "
        "ORDER BY creado DESC"
    )
    if not bandeja:
        st.caption("Vacía. Respira 😌")
    hoy_s = date.today().isoformat()
    man_s = (date.today() + timedelta(days=1)).isoformat()
    for b in bandeja:
        c1, c2, c3, c4 = st.columns([0.52, 0.16, 0.16, 0.16])
        c1.write(f"• {b['titulo']}")
        if c2.button("Hoy", key=f"bh_{b['id']}"):
            ejecutar("UPDATE items SET fecha=? WHERE id=?", (hoy_s, b["id"]))
            st.rerun()
        if c3.button("Mañana", key=f"bm_{b['id']}"):
            ejecutar("UPDATE items SET fecha=? WHERE id=?", (man_s, b["id"]))
            st.rerun()
        if c4.button("🗑", key=f"bd_{b['id']}"):
            ejecutar("UPDATE items SET estado='archivado' WHERE id=?", (b["id"],))
            st.rerun()


# ---------------------------------------------------------------- PÁGINA: ÁREAS
def pagina_areas():
    hero("Áreas de vida", "Tu vida no es solo trabajo. Estas son las partes que cuidas.", "🧩")
    for a in areas():
        pend = consultar(
            "SELECT COUNT(*) c FROM items WHERE estado='pendiente' AND area_id=?",
            (a["id"],),
        )[0]["c"]
        with st.expander(f"{a['emoji']} **{a['nombre']}** · {pend} pendientes"):
            meta = st.text_input(
                "¿Qué quieres cuidar aquí?",
                value=a["meta"] or "",
                key=f"meta_{a['id']}",
            )
            if st.button("Guardar", key=f"gm_{a['id']}"):
                ejecutar("UPDATE areas SET meta=? WHERE id=?", (meta, a["id"]))
                st.toast("Listo 🌿")

    with st.expander("➕ Agregar un área"):
        with st.form("nueva_area", clear_on_submit=True):
            n = st.text_input("Nombre")
            e = st.text_input("Emoji", value="🌱")
            m = st.text_input("¿Qué quieres cuidar?")
            ok = st.form_submit_button("Agregar")
        if ok and n.strip():
            try:
                ejecutar(
                    "INSERT INTO areas (nombre, emoji, meta) VALUES (?,?,?)",
                    (n.strip(), e.strip() or "🌱", m.strip()),
                )
                st.rerun()
            except sqlite3.IntegrityError:
                st.warning("Ya existe un área con ese nombre.")


# ---------------------------------------------------------------- PÁGINA: PROYECTOS
def pagina_proyectos():
    hero("Proyectos", "Cosas grandes que toman más de un día. No son tareas sueltas.", "📁")
    lista_areas = areas()
    etiquetas = [f"{a['emoji']} {a['nombre']}" for a in lista_areas]
    mapa = {et: a["id"] for et, a in zip(etiquetas, lista_areas)}

    with st.form("nuevo_proyecto", clear_on_submit=True):
        nombre = st.text_input("Nombre del proyecto", placeholder="Ej: organizar la mudanza")
        area_et = st.selectbox("Área", etiquetas)
        nota = st.text_input("¿Para qué? (opcional)")
        ok = st.form_submit_button("Crear proyecto")
    if ok and nombre.strip():
        ejecutar(
            "INSERT INTO proyectos (area_id, nombre, nota, creado) VALUES (?,?,?,?)",
            (mapa[area_et], nombre.strip(), nota.strip(), date.today().isoformat()),
        )
        st.rerun()

    proyectos = consultar("SELECT * FROM proyectos WHERE estado='activo' ORDER BY id DESC")
    if not proyectos:
        st.caption("Todavía no hay proyectos. Crea el primero arriba ☝️")
    for p in proyectos:
        area = consultar("SELECT emoji, nombre FROM areas WHERE id=?", (p["area_id"],))
        emoji = area[0]["emoji"] if area else "📁"
        abiertas = consultar(
            "SELECT COUNT(*) c FROM items WHERE proyecto_id=? AND estado='pendiente'",
            (p["id"],),
        )[0]["c"]
        st.markdown(
            f'<div class="card" style="margin-bottom:10px">'
            f'<b>{emoji} {p["nombre"]}</b><br>'
            f'<span style="color:#8A8071;font-size:13px">{abiertas} tareas abiertas'
            f'{" · " + p["nota"] if p["nota"] else ""}</span></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- PÁGINA: PLAN SEMANAL
def pagina_semanal():
    st.session_state.setdefault("offset_semana", 0)
    inicio = lunes() + timedelta(weeks=st.session_state["offset_semana"])
    fin = inicio + timedelta(days=6)
    hero(
        "Plan semanal",
        f"Del {fecha_es(inicio)} al {fecha_es(fin)} · decide antes de que empiece",
        "🗓️",
    )
    b1, _, b3 = st.columns([0.22, 0.56, 0.22])
    if b1.button("← Semana anterior"):
        st.session_state["offset_semana"] -= 1
        st.rerun()
    if b3.button("Semana siguiente →"):
        st.session_state["offset_semana"] += 1
        st.rerun()

    ini_s, fin_s = inicio.isoformat(), fin.isoformat()
    cap = capacidad_semana(ini_s)
    carga = carga_semana(ini_s, fin_s)

    st.markdown("### ⏳ Capacidad real por área")
    st.caption("No es lo que quieres hacer: es lo que de verdad cabe.")
    with st.form("capacidad"):
        nuevas = {}
        cols = st.columns(4)
        for i, a in enumerate(areas()):
            with cols[i % 4]:
                nuevas[str(a["id"])] = st.number_input(
                    f"{a['emoji']} {a['nombre']}",
                    0, 80, int(cap.get(a["id"], 0)), 1,
                    key=f"cap_{a['id']}",
                )
        if st.form_submit_button("Guardar capacidad"):
            guardar_semana(ini_s, capacidad={k: v for k, v in nuevas.items() if v > 0})
            st.rerun()

    total_cap = sum(cap.values()) * 60
    total_carga = sum(carga.values())
    st.markdown("### 📊 Cómo va quedando la semana")
    for a in areas():
        h_cap = cap.get(a["id"], 0) * 60
        h_carga = carga.get(a["id"], 0)
        if h_cap == 0 and h_carga == 0:
            continue
        if h_cap == 0:
            st.markdown(f"**{a['emoji']} {a['nombre']}** — {h_carga/60:.1f} h comprometidas · sin capacidad definida ⚠️")
            st.progress(1.0)
            continue
        pct = min(h_carga / h_cap, 1.0)
        st.markdown(
            f"**{a['emoji']} {a['nombre']}** — {h_carga/60:.1f} h de {h_cap/60:.1f} h"
        )
        st.progress(pct)

    if total_cap:
        pct_total = total_carga / total_cap
        if pct_total > 1:
            st.error("🚨 Esta semana no cabe. Algo tiene que salir o moverse.")
        elif pct_total > 0.85:
            st.warning("⚠️ Semana justa. Evita agregar cosas nuevas.")
        else:
            st.success("✅ Semana humanamente posible. Hay espacio para vivir.")

    semana = consultar("SELECT * FROM semanas WHERE inicio=?", (ini_s,))
    prios_guardadas = json.loads((semana[0]["prioridades"] if semana else "[]") or "[]")
    nota_actual = semana[0]["nota"] if semana else ""

    st.markdown("### 🎯 Prioridades de la semana (máx. 3)")
    items_semana = consultar(
        "SELECT id, titulo FROM items WHERE estado='pendiente' AND fecha BETWEEN ? AND ?",
        (ini_s, fin_s),
    )
    labels = {r["id"]: r["titulo"] for r in items_semana}
    sel = st.multiselect(
        "¿Qué 3 cosas harían que esta semana valga la pena?",
        list(labels.keys()),
        default=[i for i in prios_guardadas if i in labels],
        format_func=lambda i: labels[i],
        max_selections=3,
    )
    nota = st.text_input("¿Qué NO vas a hacer esta semana?", value=nota_actual)
    if st.button("Guardar plan semanal"):
        guardar_semana(ini_s, prioridades=sel, nota=nota)
        st.toast("Plan guardado. Ya es más claro 🌿")
        st.rerun()


# ---------------------------------------------------------------- PÁGINA: REVISIÓN
def pagina_revision():
    hoy = date.today()
    hero("Revisión semanal", "Cierra la semana sin juicio. Solo información.", "🔄")
    hechos = consultar("SELECT COUNT(*) c FROM items WHERE estado='hecho'")[0]["c"]
    c1, c2 = st.columns(2)
    tarjeta(c1, "Cosas hechas", hechos, "en total")
    tarjeta(c2, "Semana", fecha_es(lunes(hoy)).capitalize(), "para revisar")

    with st.form("revision", clear_on_submit=True):
        funciono = st.text_area("🌱 ¿Qué funcionó esta semana?")
        sobro = st.text_area("🍂 ¿Qué sobró y puede esperar?")
        abandono = st.text_area("🫶 ¿Qué área quedó abandonada?")
        animo = st.slider("¿Cómo te sientes con tu semana?", 1, 5, 3)
        ok = st.form_submit_button("Cerrar semana 🌙")
    if ok:
        ejecutar(
            "INSERT INTO revisiones (fecha, funciono, sobro, abandono, animo, creado) "
            "VALUES (?,?,?,?,?,?)",
            (hoy.isoformat(), funciono, sobro, abandono, animo, hoy.isoformat()),
        )
        st.success("Semana cerrada. Lo que no hiciste también es información.")

    st.markdown("### 📜 Revisiones anteriores")
    historial = consultar("SELECT * FROM revisiones ORDER BY id DESC LIMIT 5")
    if not historial:
        st.caption("Aún no hay revisiones. Haz la primera hoy 🌿")
    for r in historial:
        with st.expander(f"{r['fecha']} · ánimo {r['animo']}/5"):
            st.write(f"**Funcionó:** {r['funciono'] or '—'}")
            st.write(f"**Sobró:** {r['sobro'] or '—'}")
            st.write(f"**Área abandonada:** {r['abandono'] or '—'}")


# ---------------------------------------------------------------- MAIN
def main():
    init_db()
    if not cfg_get("onboarding"):
        onboarding()
        return

    with st.sidebar:
        st.markdown("## 🌿 Mi Semana")
        st.caption("Tu vida entera, no solo tu trabajo.")
        nav = st.radio(
            "Navegar",
            ["🏠 Hoy", "✍️ Capturar", "🧩 Áreas", "📁 Proyectos",
             "🗓️ Plan semanal", "🔄 Revisión"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        with st.expander("⚙️ Ajustes de prueba"):
            if st.button("Borrar todos los datos"):
                for tabla in ["items", "proyectos", "semanas", "revisiones", "config"]:
                    ejecutar(f"DELETE FROM {tabla}")
                st.rerun()
        st.caption("Hecho con cariño para Quilichao, Santander 🇨🇴")

    if nav.startswith("🏠"):
        pagina_hoy()
    elif nav.startswith("✍️"):
        pagina_capturar()
    elif nav.startswith("🧩"):
        pagina_areas()
    elif nav.startswith("📁"):
        pagina_proyectos()
    elif nav.startswith("🗓️"):
        pagina_semanal()
    else:
        pagina_revision()


if __name__ == "__main__":
    main()
