import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Security CRM Enterprise (Live)", layout="wide", page_icon="🛡️")

# URL de tu planilla
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-qUb6BXimV5HU4KjKXolT3M22J85QEiy_9jV0bHLkT8/edit?usp=sharing"

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Intentamos leer la planilla
        data = conn.read(spreadsheet=SHEET_URL, ttl=0)
        return data
    except Exception:
        # Si la planilla está vacía o da error, devolvemos un DataFrame vacío con las columnas
        return pd.DataFrame(columns=[
            "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
            "residencia", "grupo_familiar", "monto_sugerido", "estado", 
            "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
        ])

def save_data(dataframe):
    # Limpiamos valores nulos para evitar errores en la subida
    dataframe = dataframe.fillna("")
    conn.update(spreadsheet=SHEET_URL, data=dataframe)
    st.cache_data.clear()

# --- CARGA INICIAL ---
df = load_data()

# Si no hay datos o la planilla es nueva, inicializamos con los campos y datos semilla
if df.empty or "nombre" not in df.columns:
    st.info("Configurando estructura inicial en Google Sheets...")
    columnas = [
        "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
        "residencia", "grupo_familiar", "monto_sugerido", "estado", 
        "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
    ]
    seed_data = [
        {
            "id": 1, "nombre": "Jorge / Alex", "apellido": "Szuster", "telefono": "+54 9 11 5428-3546",
            "rubro": "Insumos Hospitalarios", "contexto": "Vende colchones, mucha plata.", 
            "residencia": "Chateau/Hacoaj", "grupo_familiar": "-", "monto_sugerido": 50000.0, 
            "estado": "1. Por contactar", "monto_confirmado": 0.0, "proximos_pasos": "Llamar semana proxima",
            "responsable": "Equipo General", "fecha_registro": datetime.now().strftime("%Y-%m-%d")
        }
    ]
    df = pd.DataFrame(seed_data, columns=columnas)
    save_data(df)
    st.rerun()

# --- CONFIGURACIÓN DE NEGOCIO ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]
LISTA_RESPONSABLES = ["Equipo General", "Julian Barki", "Ariel Goldman"]
META_PROYECTO = 500000.0

# --- NAVEGACIÓN ---
st.sidebar.title("🛡️ CRM Live")
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo"])

# --- DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Estado de Recaudación")
    
    df['monto_confirmado'] = pd.to_numeric(df['monto_confirmado'], errors='coerce').fillna(0)
    df['monto_sugerido'] = pd.to_numeric(df['monto_sugerido'], errors='coerce').fillna(0)
    
    recaudado = df['monto_confirmado'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("RECAUDADO", f"USD {recaudado:,.0f}")
    c2.metric("CONTACTOS", len(df))
    c3.metric("META RESTANTE", f"USD {max(0, META_PROYECTO - recaudado):,.0f}")

    fig = go.Figure(go.Indicator(mode="gauge+number", value=recaudado,
            gauge={'axis': {'range': [None, META_PROYECTO]}, 'bar': {'color': "#2ecc71"}},
            title={'text': "Progreso Real vs Meta"}))
    st.plotly_chart(fig, use_container_width=True)

# --- PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Gestión de Pipeline")
    busqueda = st.text_input("🔍 Buscar...")
    df_f = df[df.apply(lambda r: busqueda.lower() in str(r).lower(), axis=1)]

    for index, row in df_f.iterrows():
        with st.expander(f"👤 {row['nombre']} {row['apellido']} | {row['estado']}"):
            edit_mode = st.toggle("Modo Edición", key=f"tog_{index}")
            if not edit_mode:
                st.write(f"**Responsable:** {row['responsable']} | **Confirmado:** USD {row['monto_confirmado']}")
                st.info(f"Notas: {row['contexto']}")
            else:
                with st.form(key=f"form_{index}"):
                    f1, f2 = st.columns(2)
                    un_nom = f1.text_input("Nombre", row['nombre'])
                    un_ape = f2.text_input("Apellido", row['apellido'])
                    un_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    un_conf = f2.number_input("Monto Confirmado", value=float(row['monto_confirmado']))
                    un_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    
                    if st.form_submit_button("Guardar Cambios"):
                        df.at[index, 'nombre'] = un_nom
                        df.at[index, 'apellido'] = un_ape
                        df.at[index, 'estado'] = un_est
                        df.at[index, 'monto_confirmado'] = un_conf
                        df.at[index, 'proximos_pasos'] = un_pas
                        save_data(df)
                        st.success("Actualizado en Google Sheets")
                        st.rerun()

# --- NUEVO ---
elif menu == "🆕 Registrar Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("nuevo"):
        n = st.text_input("Nombre *")
        a = st.text_input("Apellido")
        resp = st.selectbox("Responsable", LISTA_RESPONSABLES)
        sug = st.number_input("Monto Sugerido", value=0.0)
        if st.form_submit_button("Crear"):
            if n:
                new_data = pd.DataFrame([{
                    "id": len(df) + 1, "nombre": n, "apellido": a, "responsable": resp,
                    "monto_sugerido": sug, "estado": "1. Por contactar", "monto_confirmado": 0.0,
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }]).fillna("-")
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df)
                st.success("Registrado!")
                st.rerun()
