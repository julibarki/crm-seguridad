import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Security CRM Elite", layout="wide", page_icon="🛡️")

DB_NAME = "fundraising.db"

# --- CAPA DE DATOS ---
def run_query(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return None
        return cursor.fetchall()

def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS donantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, apellido TEXT, telefono TEXT, rubro TEXT,
        contexto TEXT, residencia TEXT, grupo_familiar TEXT,
        monto_sugerido REAL DEFAULT 0, estado TEXT, 
        monto_confirmado REAL DEFAULT 0, proximos_pasos TEXT,
        responsable TEXT DEFAULT 'Equipo General',
        fecha_registro TEXT)''', commit=True)
    run_query('CREATE TABLE IF NOT EXISTS responsables (nombre TEXT UNIQUE)', commit=True)
    run_query('CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor REAL)', commit=True)
    run_query("INSERT OR IGNORE INTO ajustes VALUES ('meta_recaudacion', 500000)", commit=True)
    if not run_query("SELECT * FROM responsables"):
        run_query("INSERT INTO responsables VALUES ('Equipo General')", commit=True)

init_db()

# --- CARGA DE DATOS ---
df = pd.read_sql_query("SELECT * FROM donantes", sqlite3.connect(DB_NAME))
meta_actual = run_query("SELECT valor FROM ajustes WHERE clave = 'meta_recaudacion'")[0][0]
lista_resp = [r[0] for r in run_query("SELECT nombre FROM responsables ORDER BY nombre ASC")]
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- INTERFAZ ---
st.sidebar.title("🛡️ Security Project")
menu = st.sidebar.radio("Ir a:", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "⚙️ Configuración"])

# --- DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Estado de la Recaudación")
    recaudado = df['monto_confirmado'].sum()
    proyectado = recaudado + df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PROYECTADO", f"USD {proyectado:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, meta_actual - recaudado):,.0f}")
    c4.metric("TOTAL CONTACTOS", len(df))
    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        fig = go.Figure(go.Indicator(mode = "gauge+number+delta", value = recaudado,
            delta = {'reference': proyectado, 'position': "top", 'increasing': {'color': "blue"}},
            gauge = {'axis': {'range': [None, meta_actual]}, 'bar': {'color': "#2ecc71"}},
            title = {'text': "Progreso vs Meta"}))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        resp_money = df.groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        st.plotly_chart(px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', title="USD por Responsable"), use_container_width=True)

# --- PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Pipeline de Donantes")
    
    col_f1, col_f2 = st.columns([3, 1])
    busqueda = col_f1.text_input("🔍 Buscar por Nombre, Rubro, Notas, Familia...")
    f_resp = col_f2.selectbox("Filtrar Encargado", ["Todos"] + lista_resp)
    
    df_f = df[df.apply(lambda r: busqueda.lower() in str(r).lower(), axis=1)]
    if f_resp != "Todos": df_f = df_f[df_f['responsable'] == f_resp]

    for _, row in df_f.iterrows():
        # Iconos de estado sutiles
        emoji_estado = "🔵" if "1." in row['estado'] else "🟢" if "6." in row['estado'] else "🔴" if "7." in row['estado'] else "🟡"
        
        with st.expander(f"{emoji_estado} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            
            # --- BARRA DE ACCIONES Y DINERO (Top) ---
            c_header_1, c_header_2 = st.columns([2, 1])
            with c_header_1:
                st.markdown(f"💰 **Sugerido:** USD {row['monto_sugerido']:,.0f} | **Confirmado:** :green[USD {row['monto_confirmado']:,.0f}]")
            with c_header_2:
                # Acciones rápidas en formato pequeño
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                if col_btn1.button("✅ Conf.", key=f"q_c_{row['id']}", help="Marcar como Confirmado"):
                    run_query("UPDATE donantes SET estado='6. Donación Confirmada' WHERE id=?", (row['id'],), commit=True); st.rerun()
                if col_btn2.button("❌ Rech.", key=f"q_r_{row['id']}", help="Marcar como Rechazado"):
                    run_query("UPDATE donantes SET estado='7. Rechazó' WHERE id=?", (row['id'],), commit=True); st.rerun()
                edit_mode = col_btn3.toggle("✏️", key=f"tog_{row['id']}", help="Modo Edición")

            if not edit_mode:
                st.markdown("---")
                col_izq, col_der = st.columns([1, 1])
                
                with col_izq:
                    st.markdown("**📋 Datos del Perfil**")
                    st.markdown(f"**📞 Tel:** {row['telefono']}")
                    st.markdown(f"**💼 Rubro:** {row['rubro']}")
                    st.markdown(f"**🏠 Residencia:** {row['residencia']}")
                    st.markdown(f"**👨‍👩‍👧 Familia:** {row['grupo_familiar']}")
                    st.caption(f"Registrado el: {row.get('fecha_registro', 'N/A')}")

                with col_der:
                    st.markdown("**📓 Notas y Seguimiento**")
                    st.markdown(f"**Contexto:** {row['contexto'] if row['contexto'] else '---'}")
                    st.markdown("---")
                    st.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos'] if row['proximos_pasos'] else 'Sin definir'}]")
            
            else:
                # MODO EDICIÓN (Se mantiene completo pero dentro del toggle)
                with st.form(key=f"form_full_{row['id']}"):
                    f1, f2, f3 = st.columns(3)
                    un_nom = f1.text_input("Nombre", row['nombre'])
                    un_ape = f2.text_input("Apellido", row['apellido'])
                    un_resp = f3.selectbox("Responsable", lista_resp, index=lista_resp.index(row['responsable']) if row['responsable'] in lista_resp else 0)
                    un_rub = f1.text_input("Rubro", row['rubro'])
                    un_fam = f2.text_input("Familia", row['grupo_familiar'])
                    un_res = f3.text_input("Residencia", row['residencia'])
                    un_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']))
                    un_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                    un_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                    un_tel = f1.text_input("Teléfono", row['telefono'])
                    un_pas = f2.text_input("Próximo Paso", row['proximos_pasos'])
                    un_ctx = st.text_area("Notas de Contexto", row['contexto'])
                    if st.form_submit_button("💾 GUARDAR"):
                        run_query("""UPDATE donantes SET nombre=?, apellido=?, responsable=?, rubro=?, grupo_familiar=?, residencia=?, estado=?, monto_sugerido=?, monto_confirmado=?, telefono=?, proximos_pasos=?, contexto=? WHERE id=?""",
                                 (un_nom, un_ape, un_resp, un_rub, un_fam, un_res, un_est, un_sug, un_conf, un_tel, un_pas, un_ctx, row['id']), commit=True); st.rerun()
                
                if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                    run_query("DELETE FROM donantes WHERE id=?", (row['id'],), commit=True); st.rerun()

# --- CONFIGURACIÓN ---
elif menu == "⚙️ Configuración":
    st.title("Configuración")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎯 Meta")
        n_meta = st.number_input("Meta USD", value=float(meta_actual), step=10000.0)
        if st.button("Guardar Meta"):
            run_query("UPDATE ajustes SET valor=? WHERE clave='meta_recaudacion'", (n_meta,), commit=True); st.rerun()

        st.subheader("🆕 Registrar Nuevo")
        with st.form("new_d"):
            nn = st.text_input("Nombre *")
            na = st.text_input("Apellido")
            nr = st.selectbox("Responsable", lista_resp)
            if st.form_submit_button("Crear"):
                if nn:
                    ahora = datetime.now().strftime("%Y-%m-%d")
                    run_query("INSERT INTO donantes (nombre, apellido, responsable, estado, fecha_registro) VALUES (?,?,?,'1. Por contactar',?)", (nn, na, nr, ahora), commit=True); st.rerun()

    with c2:
        st.subheader("👥 Responsables")
        with st.form("add_res", clear_on_submit=True):
            n_res = st.text_input("Nuevo Responsable")
            if st.form_submit_button("Añadir"):
                if n_res and not run_query("SELECT * FROM responsables WHERE nombre=?", (n_res,)):
                    run_query("INSERT INTO responsables VALUES (?)", (n_res,), commit=True); st.rerun()
        for r in lista_resp:
            colr1, colr2 = st.columns([3, 1])
            colr1.write(f"• {r}")
            if r != 'Equipo General' and colr2.button("Borrar", key=f"br_{r}"):
                run_query("UPDATE donantes SET responsable='Equipo General' WHERE responsable=?", (r,), commit=True)
                run_query("DELETE FROM responsables WHERE nombre=?", (r,), commit=True); st.rerun()