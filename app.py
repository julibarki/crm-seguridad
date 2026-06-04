import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Security CRM Enterprise", layout="wide", page_icon="🛡️")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Forzamos ttl=0 para tener datos en tiempo real
        data = conn.read(ttl=0)
        if data is None or data.empty:
            raise ValueError("Vacío")
        return data
    except:
        return pd.DataFrame(columns=[
            "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
            "residencia", "grupo_familiar", "monto_sugerido", "estado", 
            "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
        ])

def save_data(dataframe):
    # Limpieza de tipos de datos antes de subir a GSheets
    dataframe = dataframe.astype(str)
    conn.update(data=dataframe)
    st.cache_data.clear()

# --- INICIALIZACIÓN ---
df = load_data()

if df.empty or "nombre" not in df.columns:
    st.info("Configurando estructura inicial en Google Sheets...")
    columnas = ["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"]
    seed = [{
        "id": "1", "nombre": "Jorge / Alex", "apellido": "Szuster", "telefono": "+54 9 11 5428-3546",
        "rubro": "Insumos Hospitalarios", "contexto": "Vende colchones.", "residencia": "Chateau", 
        "grupo_familiar": "-", "monto_sugerido": "50000", "estado": "1. Por contactar", 
        "monto_confirmado": "0", "proximos_pasos": "Llamar", "responsable": "Equipo General", 
        "fecha_registro": datetime.now().strftime("%Y-%m-%d")
    }]
    df = pd.DataFrame(seed, columns=columnas)
    save_data(df)
    st.rerun()

# --- CONFIGURACIÓN UI ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]
LISTA_RESPONSABLES = ["Equipo General", "Julian Barki", "Ariel Goldman"]

st.sidebar.title("🛡️ CRM Proyecto Seguridad")
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline", "🆕 Registro"])

if menu == "📊 Dashboard":
    st.title("Estado de Recaudación")
    confirmado = pd.to_numeric(df['monto_confirmado'], errors='coerce').fillna(0).sum()
    c1, c2 = st.columns(2)
    c1.metric("RECAUDADO REAL", f"USD {confirmado:,.0f}")
    c2.metric("TOTAL CONTACTOS", len(df))
    
    fig = go.Figure(go.Indicator(mode="gauge+number", value=confirmado,
            gauge={'axis': {'range': [None, 500000]}, 'bar': {'color': "green"}},
            title={'text': "Progreso (Meta 500k)"}))
    st.plotly_chart(fig, use_container_width=True)

elif menu == "👥 Pipeline":
    st.subheader("Gestión de Donantes")
    for index, row in df.iterrows():
        with st.expander(f"👤 {row['nombre']} {row['apellido']} | {row['estado']}"):
            if st.toggle("Editar", key=f"t_{index}"):
                with st.form(key=f"f_{index}"):
                    n_est = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    n_mon = st.number_input("Monto Confirmado", value=float(row['monto_confirmado']) if row['monto_confirmado'] != "-" else 0.0)
                    if st.form_submit_button("Guardar"):
                        df.at[index, 'estado'] = n_est
                        df.at[index, 'monto_confirmado'] = str(n_mon)
                        save_data(df)
                        st.success("¡Sincronizado con la nube!")
                        st.rerun()

elif menu == "🆕 Registro":
    with st.form("nuevo"):
        n = st.text_input("Nombre")
        if st.form_submit_button("Crear"):
            new_row = pd.DataFrame([{
                "id": str(len(df)+1), "nombre": n, "apellido": "-", "estado": "1. Por contactar", 
                "monto_confirmado": "0", "monto_sugerido": "0", "responsable": "Equipo General",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d")
            }])
            df = pd.concat([df, new_row], ignore_index=True).fillna("-")
            save_data(df)
            st.success("Añadido a Google Sheets!")
            st.rerun()
