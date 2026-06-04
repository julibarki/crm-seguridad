import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="DSVI - Security CRM", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="auto"
)

# --- CSS QUIRÚRGICO: MANTIENE EL MENÚ, BORRA GITHUB Y SHARE ---
st.markdown("""
    <style>
    /* 1. Ocultar botones de la derecha (GitHub, Share, Deploy) */
    [data-testid="stToolbar"], .stAppDeployButton {
        display: none !important;
    }
    
    /* 2. Forzar que el HEADER sea visible y NO bloquee el menú */
    header[data-testid="stHeader"] {
        visibility: visible !important;
        background-color: rgba(0,0,0,0) !important;
        z-index: 9999999 !important;
    }

    /* 3. FORZAR BOTÓN DE MENÚ (HAMBURGUESA) VISIBLE Y BLANCO */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 10000000 !important;
        color: white !important;
    }
    
    /* Asegurar que el icono dentro sea blanco puro */
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
    }

    /* 4. Quitar footer y ajustar márgenes */
    footer {visibility: hidden !important;}
    .block-container { padding-top: 3.5rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
        <style> .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 900; 
        font-size: clamp(80px, 15vw, 120px); letter-spacing: -5px; color: #FFFFFF; text-align: center; margin-top: 80px; } </style>
        <div class="logo-text">DSVI</div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            password_input = st.text_input("Clave de acceso:", type="password")
            if st.button("Ingresar", use_container_width=True):
                if password_input == st.secrets["auth"]["password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta")
    return False

# --- SISTEMA PRINCIPAL ---
if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
    ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

    def load_data():
        try:
            data = conn.read(ttl=0)
            if data is None or data.empty:
                return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
            data.columns = [str(c).strip() for c in data.columns]
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
            dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
            conn.update(data=dataframe.astype(str))
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error: {e}"); return False

    def make_whatsapp_link(phone, name):
        clean_phone = ''.join(filter(str.isdigit, str(phone)))
        msg = urllib.parse.quote(f"Hola {name}, ¿cómo estás? Te contacto de DSVI...")
        return f"https://wa.me/{clean_phone}?text={msg}"

    df = load_data()

    # --- SIDEBAR ---
    st.sidebar.title("🛡️ CRM DSVI")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    
    st.sidebar.markdown("---")
    meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
    menu = st.sidebar.radio("Navegación:", ["📊 Dashboard", "👥 Pipeline", "🆕 Registro"])
    if st.sidebar.button("🔄 Sincronizar", use_container_width=True): st.cache_data.clear(); st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Panel de Control Estratégico")
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
        faltante = max(0, meta_usd - recaudado)
        c1, c2, c3 = st.columns(3)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("META FALTANTE", f"USD {faltante:,.0f}")
        c3.metric("TOTAL CONTACTOS", len(df))
        
        st.markdown("---")
        col_gauge, col_resp = st.columns([1, 1.2])
        with col_gauge:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=recaudado,
                gauge={'axis': {'range': [0, meta_usd]}, 'bar': {'color': "#2ecc71"}, 'bgcolor': "rgba(0,0,0,0)"},
                title={'text': "Avance General"}))
            fig.update_layout(height=350, margin=dict(l=60, r=60, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig, use_container_width=True)
        
        with col_resp:
            st.subheader("USD por Responsable")
            resp_money = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
            if not resp_money.empty:
                st.plotly_chart(px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db']), use_container_width=True)

        st.subheader("🏆 Tabla de Honor (Confirmados)")
        df_honor = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado', 'responsable']].sort_values(by='monto_confirmado', ascending=False)
        st.dataframe(df_honor, use_container_width=True, hide_index=True)

    # --- PIPELINE ---
    elif menu == "👥 Pipeline":
        st.title("Gestión de Prospectos")
        search = st.text_input("🔍 Buscar por cualquier campo...").lower()
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df
        
        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                
                c_h1, c_h2 = st.columns([2, 1])
                with c_h1:
                    st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                with c_h2:
                    wa_url = make_whatsapp_link(row['telefono'], row['nombre'])
                    st.markdown(f"[![WA](https://img.shields.io/badge/WhatsApp-25D366?style=flat&logo=whatsapp&logoColor=white)]({wa_url})")

                is_edit = st.toggle("✏️ Editar Ficha", key=f"ed_{row['id']}")
                if not is_edit:
                    st.markdown("---")
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.write(f"📞 **Tel:** {row['telefono']}")
                        st.write(f"💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']}")
                        st.write(f"👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                    with col_r:
                        st.write(f"📓 **Contexto:** {row['contexto']}")
                        st.write(f"🚀 **Paso:** :orange[{row['proximos_pasos']}]")
                        st.caption(f"📅 Reg: {row.get('fecha_registro','-')}")
                else:
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2, f3 = st.columns(3)
                        u_nom = f1.text_input("Nombre", row['nombre']); u_ape = f2.text_input("Apellido", row['apellido']); u_tel = f3.text_input("Teléfono", row['telefono'])
                        u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                        u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0); u_rub = f3.text_input("Rubro", row['rubro'])
                        u_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido'])); u_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado'])); u_res = f3.text_input("Residencia", row['residencia'])
                        u_fam = f1.text_input("Familia", row['grupo_familiar']); u_pas = f2.text_input("Próximo Paso", row['proximos_pasos']); u_ctx = st.text_area("Contexto", row['contexto'])
                        if st.form_submit_button("💾 GUARDAR"):
                            target_id = str(row['id'])
                            df.loc[df['id'] == target_id, ['nombre','apellido','responsable','estado','monto_sugerido','monto_confirmado','telefono','residencia','grupo_familiar','rubro','contexto','proximos_pasos']] = [u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_ctx, u_pas]
                            if save_data(df): st.rerun()
                    if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                        df = df[df['id'] != str(row['id'])]
                        if save_data(df): st.rerun()

    # --- NUEVO ---
    elif menu == "🆕 Registro":
        st.subheader("Cargar Nuevo Prospecto")
        with st.form("n_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre *"); a = c2.text_input("Apellido")
            r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES); s = c2.number_input("Sugerido (USD)", value=0.0)
            ctx = st.text_area("Notas de contexto")
            if st.form_submit_button("🚀 Crear Donante"):
                if n:
                    new_id = str(int(datetime.now().timestamp()))
                    new_row = pd.DataFrame([{"id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"), "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-" }])
                    if save_data(pd.concat([df, new_row], ignore_index=True)): st.success("¡Registrado!"); st.rerun()
