import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="DSVI - CRM Elite v6.0", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- ESTILO DSVI Y AJUSTES VISUALES ---
st.markdown("""
    <style>
    footer {visibility: hidden !important;}
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 800 !important; }
    .block-container { padding-top: 2rem !important; }
    .wa-icon:hover { transform: scale(1.1); transition: 0.2s; }
    /* Estrellas doradas */
    .star-rating { color: #FBBF24; font-weight: bold; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

# --- UTILITARIO DE ESTRELLAS ---
def render_stars(rating):
    try:
        r = int(float(rating))
        return "⭐" * r if r > 0 else "---"
    except:
        return "---"

# --- FUNCIÓN DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("""
        <style> .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 900; 
        font-size: 100px; letter-spacing: -5px; color: #FFFFFF; text-align: center; margin-top: 80px; } </style>
        <div class="logo-text">DSVI</div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #9CA3AF;'>SISTEMA DE GESTIÓN PRIVADO</p>", unsafe_allow_html=True)
            password_input = st.text_input("Ingresa la clave:", type="password")
            if st.button("Ingresar", use_container_width=True):
                if password_input == st.secrets["auth"]["password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta")
    return False

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
    ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

    def load_data():
        try:
            data = conn.read(ttl=0)
            if data is None or data.empty: return pd.DataFrame()
            data.columns = [str(c).strip() for c in data.columns]
            # Asegurar nuevas columnas Sergio con valor inicial 3
            for m in ["ascendencia", "capacidad", "red_contactos"]:
                if m not in data.columns: data[m] = "3"
            for col in ['monto_confirmado', 'monto_sugerido']:
                if col in data.columns: data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
            for col in data.columns:
                if col not in ['monto_confirmado', 'monto_sugerido']:
                    data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
                    data[col] = data[col].str.replace(r'\.0$', '', regex=True)
            return data
        except: return pd.DataFrame()

    def save_data(dataframe):
        try:
            if 'estado' in dataframe.columns and 'monto_confirmado' in dataframe.columns:
                dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
            conn.update(data=dataframe.astype(str))
            st.cache_data.clear()
            return True
        except: return False

    def make_whatsapp_link(phone, name):
        clean_phone = ''.join(filter(str.isdigit, str(phone)))
        if not clean_phone or clean_phone == "-": return None
        msg = urllib.parse.quote(f"Hola {name}, ¿cómo estás? Te contacto de DSVI...")
        return f"https://wa.me/{clean_phone}?text={msg}"

    df = load_data()

    # --- SIDEBAR ---
    st.sidebar.title("🛡️ CRM DSVI Elite")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
    menu = st.sidebar.radio("Navegación:", ["📊 Dashboard", "👥 Pipeline Operativo", "🔎 Análisis Consultoría", "🆕 Registro Nuevo"])
    if st.sidebar.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Panel Ejecutivo")
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("META FALTANTE", f"USD {max(0, meta_usd - recaudado):,.0f}")
        c3.metric("CONTACTOS", len(df))
        st.markdown("---")
        col_g, col_r = st.columns([1, 1.2])
        with col_g:
            fig_g = go.Figure(go.Indicator(mode="gauge+number", value=recaudado,
                gauge={'axis': {'range': [0, meta_usd]}, 'bar': {'color': "#10B981"}, 'bgcolor': "rgba(255,255,255,0.05)"},
                title={'text': "Progreso"}))
            fig_g.update_layout(height=350, margin=dict(l=40, r=40, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_g, use_container_width=True)
        with col_r:
            st.subheader("USD por Responsable")
            resp_m = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
            if not resp_m.empty:
                st.plotly_chart(px.bar(resp_m, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3B82F6']), use_container_width=True)
        st.subheader("🏆 Tabla de Honor")
        df_honor = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado', 'responsable']].sort_values(by='monto_confirmado', ascending=False)
        st.dataframe(df_honor, use_container_width=True, hide_index=True, column_config={"monto_confirmado": st.column_config.NumberColumn("USD", format="$ %.0f")})

    # --- PIPELINE ---
    elif menu == "👥 Pipeline Operativo":
        st.title("Gestión de Prospectos")
        search = st.text_input("🔍 Buscar...").lower()
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df
        
        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                
                c_h1, c_h2 = st.columns([2, 1])
                with c_h1:
                    st.markdown(f"💰 **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                    # RENDER DE ESTRELLAS DE SERGIO
                    st.markdown(f"⭐ **Asc:** {render_stars(row['ascendencia'])} | 💰 **Cap:** {render_stars(row['capacidad'])} | 🌐 **Red:** {render_stars(row['red_contactos'])}")
                with c_h2:
                    wa_url = make_whatsapp_link(row['telefono'], row['nombre'])
                    if wa_url:
                        st.markdown(f'<a href="{wa_url}" target="_blank"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="35" class="wa-icon"></a>', unsafe_allow_html=True)

                if st.toggle("✏️ Editar", key=f"ed_{row['id']}"):
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2, f3 = st.columns(3)
                        u_nom = f1.text_input("Nombre", row['nombre']); u_ape = f2.text_input("Apellido", row['apellido']); u_tel = f3.text_input("Teléfono", row['telefono'])
                        u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                        u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0); u_rub = f3.text_input("Rubro", row['rubro'])
                        u_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido'])); u_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado'])); u_res = f3.text_input("Residencia", row['residencia'])
                        u_fam = f1.text_input("Familia", row['grupo_familiar']); u_pas = f2.text_input("Próximo Paso", row['proximos_pasos']); u_ctx = st.text_area("Contexto", row['contexto'])
                        # CALIFICACIÓN POR ESTRELLAS EN EDICIÓN
                        st.markdown("---")
                        st.markdown("**Calificación Estratégica (Escala 1 a 5)**")
                        s_c1, s_c2, s_c3 = st.columns(3)
                        u_asc = s_c1.slider("Ascendencia", 1, 5, int(float(row['ascendencia'])) if row['ascendencia'].isdigit() else 3, key=f"s1_{row['id']}")
                        u_cap = s_c2.slider("Capacidad Econ.", 1, 5, int(float(row['capacidad'])) if row['capacidad'].isdigit() else 3, key=f"s2_{row['id']}")
                        u_red = s_c3.slider("Red de Contactos", 1, 5, int(float(row['red_contactos'])) if row['red_contactos'].isdigit() else 3, key=f"s3_{row['id']}")
                        
                        if st.form_submit_button("💾 GUARDAR"):
                            target_id = str(row['id'])
                            df.loc[df['id'] == target_id, ['nombre','apellido','responsable','estado','monto_sugerido','monto_confirmado','telefono','residencia','grupo_familiar','rubro','contexto','proximos_pasos','ascendencia','capacidad','red_contactos']] = [u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_ctx, u_pas, str(u_asc), str(u_cap), str(u_red)]
                            if save_data(df): st.rerun()
                    if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                        df = df[df['id'] != str(row['id'])]
                        if save_data(df): st.rerun()
                else:
                    st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")

    # --- VISTA: CONSULTORIA ---
    elif menu == "🔎 Análisis Consultoría":
        st.title("Métricas de Priorización")
        st.markdown("Tabla diseñada para el trabajo estratégico de Sergio.")
        df_sergio = df.copy()
        # Transformamos números a estrellas para la tabla
        df_sergio['⭐ Ascendencia'] = df_sergio['ascendencia'].apply(render_stars)
        df_sergio['💰 Capacidad'] = df_sergio['capacidad'].apply(render_stars)
        df_sergio['🌐 Red'] = df_sergio['red_contactos'].apply(render_stars)
        
        st.dataframe(df_sergio[['nombre', 'apellido', '⭐ Ascendencia', '💰 Capacidad', '🌐 Red', 'monto_sugerido', 'responsable']], use_container_width=True, hide_index=True)

    # --- VISTA: NUEVO ---
    elif menu == "🆕 Registro Nuevo":
        st.subheader("Cargar Nuevo Prospecto")
        with st.form("n_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre *"); a = c2.text_input("Apellido")
            r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES); s = c2.number_input("Sugerido (USD)", value=0.0)
            st.markdown("---")
            st.markdown("**Calificación Inicial Sergio (1 a 5)**")
            s_1, s_2, s_3 = st.columns(3)
            asc = s_1.select_slider("Ascendencia", options=[1,2,3,4,5], value=3)
            cap = s_2.select_slider("Capacidad Econ.", options=[1,2,3,4,5], value=3)
            red = s_3.select_slider("Red de Contactos", options=[1,2,3,4,5], value=3)
            ctx = st.text_area("Notas de contexto")
            if st.form_submit_button("🚀 Crear Donante"):
                if n:
                    new_id = str(int(datetime.now().timestamp()))
                    new_row = pd.DataFrame([{"id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"), "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-", "ascendencia": str(asc), "capacidad": str(cap), "red_contactos": str(red) }])
                    if save_data(pd.concat([df, new_row], ignore_index=True)): st.success("¡Registrado!"); st.rerun()
