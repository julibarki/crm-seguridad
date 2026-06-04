import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Elite - Business Intelligence", layout="wide", page_icon="🛡️")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            raise ValueError("Vacío")
        # Aseguramos que los montos sean numéricos para evitar errores de suma
        data['monto_confirmado'] = pd.to_numeric(data['monto_confirmado'], errors='coerce').fillna(0)
        data['monto_sugerido'] = pd.to_numeric(data['monto_sugerido'], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame(columns=[
            "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
            "residencia", "grupo_familiar", "monto_sugerido", "estado", 
            "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
        ])

def save_data(dataframe):
    # Regla de Integridad: Si no es "Confirmada", el monto confirmado DEBE ser 0
    # Esto limpia la base de datos antes de subirla
    dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
    
    # Guardar como texto para Google Sheets
    dataframe_to_save = dataframe.astype(str)
    conn.update(data=dataframe_to_save)
    st.cache_data.clear()

# --- CONSTANTES ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- INICIALIZACIÓN ---
df = load_data()

# Lógica de Responsables
responsables_existentes = sorted(df['responsable'].unique().tolist())
if "Equipo General" not in responsables_existentes:
    responsables_existentes = ["Equipo General"] + responsables_existentes

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta Objetivo (USD)", value=500000, step=10000)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Estratégico", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo"])

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard Estratégico":
    st.title("Análisis de Recaudación Real")
    
    # MÉTRICAS PURAS (Filtradas por lógica de negocio)
    confirmado_real = df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()
    en_negociacion = df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()
    dinero_perdido = df[df['estado'] == "7. Rechazó"]['monto_sugerido'].sum()
    proyectado_total = confirmado_real + en_negociacion
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO (CONFIRMADO)", f"USD {confirmado_real:,.0f}")
    c2.metric("POTENCIAL CERCANO", f"USD {en_negociacion:,.0f}", help="Suma de montos sugeridos de gente en negociación")
    c3.metric("DINERO PERDIDO (RECHAZOS)", f"USD {dinero_perdido:,.0f}", delta=float(-dinero_perdido), delta_color="inverse")
    c4.metric("TOTAL PROYECTADO", f"USD {proyectado_total:,.0f}")

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    
    with col_a:
        # Gráfico Gauge: Solo el verde es dinero real en mano
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=confirmado_real,
            delta={'reference': proyectado_total, 'position': "top", 'increasing': {'color': "blue"}, 'title': {'text': "Proyección"}},
            gauge={'axis': {'range': [None, meta_usd]}, 'bar': {'color': "#2ecc71"}},
            title={'text': "Progreso Real vs Meta"}))
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        st.subheader("Efectividad por Responsable")
        # Sumamos solo lo confirmado de verdad
        resp_perf = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().reset_index()
        if not resp_perf.empty:
            st.plotly_chart(px.bar(resp_perf, x='monto_confirmado', y='responsable', orientation='h', title="USD Recaudados"), use_container_width=True)
        else:
            st.info("Aún no hay donaciones confirmadas.")

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Gestión de Pipeline")
    
    search = st.text_input("🔍 Buscar (Nombre, Rubro, Notas...)").lower()
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)]

    for index, row in df_f.iterrows():
        # Indicador visual de alerta si hay inconsistencia (dinero en estado no confirmado)
        alerta = "⚠️" if (row['monto_confirmado'] > 0 and row['estado'] != "6. Donación Confirmada") else ""
        emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
        
        with st.expander(f"{alerta} {emoji} {row['nombre']} {row['apellido']} | {row['estado']}"):
            
            c_h1, c_h2 = st.columns([2, 1])
            with c_h1:
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            with c_h2:
                col_b1, col_b2, col_b3 = st.columns(3)
                if col_b1.button("✅", key=f"q_c_{index}", help="Confirmar Donación"):
                    df.at[index, 'estado'] = '6. Donación Confirmada'
                    # No reseteamos monto aquí para que el usuario pueda cargarlo
                    save_data(df); st.rerun()
                if col_b2.button("❌", key=f"q_r_{index}", help="Marcar Rechazo (Resetea Monto a 0)"):
                    df.at[index, 'estado'] = '7. Rechazó'
                    df.at[index, 'monto_confirmado'] = 0 # REGLA DE NEGOCIO: Rechazo = $0
                    save_data(df); st.rerun()
                edit_mode = col_b3.toggle("✏️", key=f"tog_{index}")

            if not edit_mode:
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📞 Tel:** {row['telefono']} | **💼 Rubro:** {row['rubro']}")
                    st.write(f"**🏠 Residencia:** {row['residencia']} | **👨‍👩‍👧 Familia:** {row['grupo_familiar']}")
                with col2:
                    st.write(f"**📓 Contexto:** {row['contexto']}")
                    st.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_ed_{index}"):
                    f1, f2, f3 = st.columns(3)
                    u_nom = f1.text_input("Nombre", row['nombre'])
                    u_ape = f2.text_input("Apellido", row['apellido'])
                    u_tel = f3.text_input("Teléfono", row['telefono'])
                    
                    u_resp = f1.selectbox("Responsable", responsables_existentes, index=responsables_existentes.index(row['responsable']) if row['responsable'] in responsables_existentes else 0)
                    u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    u_sug = f3.number_input("Sugerido", value=float(row['monto_sugerido']))
                    
                    # El campo de monto confirmado solo debería ser > 0 si el estado es confirmado
                    u_conf = f1.number_input("Confirmado (Solo si el estado es '6. Donación Confirmada')", value=float(row['monto_confirmado']))
                    
                    u_pas = f2.text_input("Próximo Paso", row['proximos_pasos'])
                    u_ctx = st.text_area("Contexto", row['contexto'])
                    
                    if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                        # Aplicamos la lógica de negocio antes de guardar
                        final_conf = u_conf if u_est == "6. Donación Confirmada" else 0
                        df.at[index, 'nombre'] = u_nom
                        df.at[index, 'apellido'] = u_ape
                        df.at[index, 'estado'] = u_est
                        df.at[index, 'monto_confirmado'] = final_conf
                        df.at[index, 'monto_sugerido'] = u_sug
                        df.at[index, 'responsable'] = u_resp
                        df.at[index, 'telefono'] = u_tel
                        df.at[index, 'proximos_pasos'] = u_pas
                        df.at[index, 'contexto'] = u_ctx
                        save_data(df); st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Registrar Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("nuevo_prospecto"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        resp = c1.selectbox("Asignar Responsable", responsables_existentes)
        sug = c2.number_input("Monto Sugerido", value=0.0)
        ctx = st.text_area("Notas de contexto")
        
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                new_row = pd.DataFrame([{
                    "id": str(len(df) + 1), "nombre": n, "apellido": a, "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", 
                    "monto_sugerido": str(sug), "estado": "1. Por contactar", "monto_confirmado": "0", "proximos_pasos": "-", "responsable": resp, "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df); st.success("¡Registrado!"); st.rerun()
