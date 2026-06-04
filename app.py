import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="DSVI - Security CRM", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="auto"
)

# --- CSS DEFINITIVO: OCULTA GITHUB, PERO DEJA EL MENÚ LIBRE ---
st.markdown("""
    <style>
    /* 1. Ocultamos el bloque de herramientas de la DERECHA (GitHub, Share, etc) */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* 2. Ocultamos el botón de Deploy (azul) */
    .stAppDeployButton {
        display: none !important;
    }

    /* 3. Mantenemos el Header pero lo hacemos transparente para que el botón sea clickeable */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: white !important;
    }

    /* 4. Forzamos que el botón del Menú (hamburguesa) sea visible y de color BLANCO */
    button[data-testid="stBaseButton-headerNoPadding"] {
        color: white !important;
        visibility: visible !important;
        display: block !important;
    }
    
    /* 5. Quitamos el pie de página de Streamlit */
    footer {visibility: hidden !important;}

    /* 6. Espacio para que el contenido no choque con el botón de menú arriba */
    .block-container {
        padding-top: 3rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Logo DSVI en blanco puro
    st.markdown("""
        <style>
        .logo-text {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-weight: 900;
            font-size: clamp(80px, 15vw, 130px);
            letter-spacing: -5px;
            color: #FFFFFF;
            text-align: center;
            margin-bottom: 20px;
            margin-top: 80px;
        }
        </style>
        <div class="logo-text">DSVI</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            password_input = st.text_input("Ingresa la clave de acceso:", type="password")
            if st.button("Ingresar", use_container_width=True):
                if password_input == st.secrets["auth"]["password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta")
    return False

# --- VALIDACIÓN DE ACCESO ---
if check_password():
    
    # --- CONEXIÓN ---
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- CONFIGURACIÓN ---
    LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
    ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

    def load_data():
        try:
            data = conn.read(ttl=0)
            if data is None or data.empty:
                return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
            data.columns = [str(c).strip() for c in data.columns]
            for col in ['monto_confirmado', 'monto_sugerido']:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
            for col in data.columns:
                if col not in ['monto_confirmado', 'monto_sugerido']:
                    data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
                    data[col] = data[col].str.replace(r'\.0$', '', regex=True)
            return data
        except Exception:
            return pd.DataFrame()

    def save_data(dataframe):
        try:
            if 'estado' in dataframe.columns and 'monto_confirmado' in dataframe.columns:
                dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
            df_save = dataframe.astype(str)
            conn.update(data=df_save)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error: {e}")
            return False

    df = load_data()

    # --- SIDEBAR (MENÚ LATERAL) ---
    st.sidebar.title("🛡️ CRM Recaudación")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.sidebar.markdown("---")
    meta_usd = st.sidebar.number_input("Meta Global (USD)", value=24000.0, step=10000.0)
    menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline", "🆕 Registro"])
    
    if st.sidebar.button("🔄 Sincronizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Panel de Control")
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("CONTACTOS", len(df))
        c3.metric("% LOGRADO", f"{(recaudado/meta_usd*100):,.1f}%")
        
        st.markdown("---")
        fig = go.Figure(go.Indicator(mode="gauge+number", value=recaudado,
            gauge={'axis': {'range': [0, meta_usd]}, 'bar': {'color': "#2ecc71"}, 'bgcolor': "rgba(0,0,0,0)"},
            title={'text': "Progreso"}))
        fig.update_layout(height=350, margin=dict(l=60, r=60, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🏆 Donaciones Confirmadas")
        df_honor = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado']].sort_values(by='monto_confirmado', ascending=False)
        st.dataframe(df_honor, use_container_width=True, hide_index=True)

    # --- PIPELINE ---
    elif menu == "👥 Pipeline":
        st.title("Gestión de Prospectos")
        search = st.text_input("🔍 Buscar...").lower()
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df
        
        for idx, row in df_f.iterrows():
            with st.expander(f"👤 {row['nombre']} {row['apellido']} | {row['estado']}"):
                st.write(f"💰 **Confirmado:** USD {float(row['monto_confirmado']):,.0f}")
                if st.toggle("Editar", key=f"ed_{row['id']}"):
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2 = st.columns(2)
                        u_nom = f1.text_input("Nombre", row['nombre']); u_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                        u_conf = f2.number_input("Monto", value=float(row['monto_confirmado']))
                        if st.form_submit_button("Guardar"):
                            target_id = str(row['id'])
                            df.loc[df['id'] == target_id, ['nombre', 'estado', 'monto_confirmado']] = [u_nom, u_est, u_conf]
                            if save_data(df): st.rerun()
                else:
                    st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")

    # --- NUEVO ---
    elif menu == "🆕 Registro":
        st.subheader("Cargar Nuevo")
        with st.form("n_form", clear_on_submit=True):
            n = st.text_input("Nombre *"); a = st.text_input("Apellido")
            r = st.selectbox("Responsable", LISTA_RESPONSABLES)
            if st.form_submit_button("Crear"):
                if n:
                    new_id = str(int(datetime.now().timestamp()))
                    new_row = pd.DataFrame([{"id": new_id, "nombre": n, "apellido": a, "responsable": r, "estado": "1. Por contactar", "monto_confirmado": 0.0, "monto_sugerido": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"), "telefono": "-", "rubro": "-", "contexto": "-", "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-" }])
                    if save_data(pd.concat([df, new_row], ignore_index=True)): st.success("¡Registrado!"); st.rerun()
