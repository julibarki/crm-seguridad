import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="DSVI CRM - Elite v9.0", 
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
    .log-entry { background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid #1E3A8A; font-size: 14px; }
    /* Ajuste para que el menú mobile sea visible */
    [data-testid="stSidebarCollapsedControl"] { color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- UTILITARIOS ---
def render_stars(rating):
    try:
        r = int(float(rating))
        return "⭐" * r if r > 0 else "---"
    except: return "---"

def get_urgencia_label(fecha_str):
    try:
        if not fecha_str or str(fecha_str) == "-": return ""
        fecha_dt = datetime.strptime(str(fecha_str), "%Y-%m-%d")
        dias = (datetime.now() - fecha_dt).days
        if dias >= 7: return " 🚨"
        if dias >= 3: return " ⚠️"
        return ""
    except: return ""

# --- FUNCIÓN DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    st.markdown("""
        <style> .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 900; 
        font-size: 100px; letter-spacing: -5px; color: #FFFFFF; text-align: center; margin-top: 80px; } </style>
        <div class="logo-text">DSVI</div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #9CA3AF;'>SISTEMA DE GESTIÓN PRIVADO</p>", unsafe_allow_html=True)
            password_input = st.text_input("Contraseña:", type="password")
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
    VALORES_METRICAS = ["1", "2", "3", "4", "5"]

    def load_data():
        try:
            data = conn.read(ttl=0)
            if data is None or data.empty: return pd.DataFrame()
            data.columns = [str(c).strip() for c in data.columns]
            if "ascendencia" in data.columns: data = data.rename(columns={"ascendencia": "comunidad"})
            for m in ["comunidad", "capacidad", "red_contactos", "bitacora", "ultima_gestion"]:
                if m not in data.columns: data[m] = "-"
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
        return f"https://wa.me/{clean_phone}"

    df = load_data()

    # --- SIDEBAR ---
    st.sidebar.title("🛡️ CRM DSVI Pro")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
    menu = st.sidebar.radio("Navegación:", ["📊 Dashboard", "👥 Pipeline Operativo", "🔎 Análisis Consultoría", "🆕 Registro Nuevo"])
    if st.sidebar.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()

    # --- VISTA: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Panel Ejecutivo de Recaudación")
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("META FALTANTE", f"USD {max(0, meta_usd - recaudado):,.0f}")
        c3.metric("CONTACTOS", len(df))
        
        st.markdown("---")
        
        # Gráfico Gauge Centralizado
        fig_g = go.Figure(go.Indicator(mode="gauge+number", value=recaudado,
            gauge={'axis': {'range': [0, meta_usd]}, 'bar': {'color': "#10B981"}, 'bgcolor': "rgba(255,255,255,0.05)"},
            title={'text': "Progreso vs Meta"}))
        fig_g.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_g, use_container_width=True)

        st.subheader("🏆 Tabla de Honor (Donaciones Confirmadas)")
        df_honor = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado', 'responsable']].sort_values(by='monto_confirmado', ascending=False)
        if not df_honor.empty:
            st.dataframe(df_honor, use_container_width=True, hide_index=True, column_config={"monto_confirmado": st.column_config.NumberColumn("Monto USD", format="$ %.0f")})
        else: st.info("No hay donaciones confirmadas para mostrar aún.")

    # --- VISTA: PIPELINE ---
    elif menu == "👥 Pipeline Operativo":
        st.title("Gestión de Prospectos")
        
        # MEJORA: Filtros Rápidos
        f_col1, f_col2 = st.columns(2)
        filtro_resp = f_col1.multiselect("Filtrar por Responsable", LISTA_RESPONSABLES, default=LISTA_RESPONSABLES)
        filtro_est = f_col2.multiselect("Filtrar por Estado", ESTADOS, default=ESTADOS)
        
        search = st.text_input("🔍 Buscar por Nombre, Notas o Familia...").lower()
        
        # Aplicar filtros
        df_f = df[df['responsable'].isin(filtro_resp) & df['estado'].isin(filtro_est)]
        if search:
            df_f = df_f[df_f.apply(lambda r: search in str(r).lower(), axis=1)]

        st.caption(f"Mostrando {len(df_f)} de {len(df)} contactos.")

        for idx, row in df_f.iterrows():
            urg_icon = get_urgencia_label(row['ultima_gestion'])
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            
            # MEJORA: Obtener última nota para el header
            last_note = ""
            if str(row['bitacora']) != "-":
                parts = str(row['bitacora']).split(" | ")
                if parts:
                    last_note = f" | 💬 {parts[0][:40]}..." # Tomamos los primeros 40 caracteres

            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['responsable']}{urg_icon}{last_note}"):
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"💰 **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                with c2:
                    wa_url = make_whatsapp_link(row['telefono'], row['nombre'])
                    if wa_url:
                        st.markdown(f'<a href="{wa_url}" target="_blank"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="35" class="wa-icon"></a>', unsafe_allow_html=True)
                
                is_edit = st.toggle("✏️ Editar / Registrar Gestión", key=f"ed_{row['id']}")
                if not is_edit:
                    st.markdown("---")
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                        st.write(f"⭐ **Comunidad:** {render_stars(row['comunidad'])} | 💰 **Capacidad:** {render_stars(row['capacidad'])}")
                    with col_r:
                        st.write(f"🚀 **Próximo:** :orange[{row['proximos_pasos']}]")
                        st.caption(f"📅 Última Gestión: {row['ultima_gestion']}")
                    
                    st.markdown("**📜 Historial de Gestión**")
                    bit_str = str(row['bitacora'])
                    if bit_str and bit_str != "-":
                        for entry in bit_str.split(" | "):
                            if entry.strip(): st.markdown(f'<div class="log-entry">{entry}</div>', unsafe_allow_html=True)
                else:
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2, f3 = st.columns(3)
                        u_nom = f1.text_input("Nombre", row['nombre']); u_ape = f2.text_input("Apellido", row['apellido']); u_tel = f3.text_input("Teléfono", row['telefono'])
                        u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                        u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0); u_rub = f3.text_input("Rubro", row['rubro'])
                        u_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido'])); u_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado'])); u_res = f3.text_input("Residencia", row['residencia'])
                        u_fam = f1.text_input("Familia", row['grupo_familiar']); u_pas = f2.text_input("Próximo Paso", row['proximos_pasos'])
                        st.markdown("📝 **Nueva Nota de Gestión**")
                        new_note = st.text_input("¿Qué novedades hay hoy?")
                        st.markdown("---")
                        st.markdown("**Calificación Estratégica (1 a 5)**")
                        sc1, sc2, sc3 = st.columns(3)
                        u_com = sc1.slider("Comunidad", 1, 5, int(float(row['comunidad'])) if str(row['comunidad']).isdigit() else 3, key=f"s1_{row['id']}")
                        u_cap = sc2.slider("Capacidad", 1, 5, int(float(row['capacidad'])) if str(row['capacidad']).isdigit() else 3, key=f"s2_{row['id']}")
                        u_red = sc3.slider("Red", 1, 5, int(float(row['red_contactos'])) if str(row['red_contactos']).isdigit() else 3, key=f"s3_{row['id']}")
                        if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                            fecha_hoy = datetime.now().strftime("%d/%m")
                            bit_actual = str(row['bitacora']) if str(row['bitacora']) != "-" else ""
                            if new_note:
                                ne = f"[{fecha_hoy}] {new_note}"
                                bit_actual = f"{ne} | {bit_actual}" if bit_actual else ne
                            df.loc[df['id'] == str(row['id']), ['nombre','apellido','responsable','estado','monto_sugerido','monto_confirmado','telefono','residencia','grupo_familiar','rubro','proximos_pasos','comunidad','capacidad','red_contactos','bitacora','ultima_gestion']] = [u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_pas, str(u_com), str(u_cap), str(u_red), bit_actual, datetime.now().strftime("%Y-%m-%d")]
                            if save_data(df): st.rerun()
                    if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                        df = df[df['id'] != str(row['id'])]
                        if save_data(df): st.rerun()

    # --- VISTA: CONSULTORIA ---
    elif menu == "🔎 Análisis Consultoría":
        st.title("Métricas de Priorización")
        df_sergio = df.copy()
        df_sergio['⭐ Comunidad'] = df_sergio['comunidad'].apply(render_stars)
        df_sergio['💰 Capacidad'] = df_sergio['capacidad'].apply(render_stars)
        df_sergio['🌐 Red'] = df_sergio['red_contactos'].apply(render_stars)
        st.dataframe(df_sergio[['nombre', 'apellido', '⭐ Comunidad', '💰 Capacidad', '🌐 Red', 'monto_sugerido', 'responsable']], use_container_width=True, hide_index=True)

    # --- VISTA: NUEVO ---
    elif menu == "🆕 Registro Nuevo":
        st.subheader("Cargar Nuevo Prospecto")
        with st.form("n_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre *"); a = c2.text_input("Apellido")
            r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES); s = c2.number_input("Sugerido (USD)", value=0.0)
            st.markdown("---")
            s1, s2, s3 = st.columns(3)
            com = s1.select_slider("Comunidad", options=[1,2,3,4,5], value=3)
            cap = s2.select_slider("Capacidad", options=[1,2,3,4,5], value=3)
            red = s3.select_slider("Red", options=[1,2,3,4,5], value=3)
            ctx = st.text_area("Notas iniciales")
            if st.form_submit_button("🚀 Crear Donante"):
                if n:
                    new_id = str(int(datetime.now().timestamp()))
                    hoy = datetime.now().strftime("%Y-%m-%d")
                    bit = f"[{datetime.now().strftime('%d/%m')}] Registro inicial"
                    if ctx: bit = f"[{datetime.now().strftime('%d/%m')}] Creado: {ctx} | {bit}"
                    new_row = pd.DataFrame([{"id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": hoy, "ultima_gestion": hoy, "telefono": "-", "rubro": "-", "bitacora": bit, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-", "comunidad": str(com), "capacidad": str(cap), "red_contactos": str(red) }])
                    if save_data(pd.concat([df, new_row], ignore_index=True)): st.success("¡Registrado!"); st.rerun()
