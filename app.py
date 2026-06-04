import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Security CRM Enterprise (Live)", layout="wide", page_icon="🛡️")

# URL de tu planilla (la que me pasaste)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-qUb6BXimV5HU4KjKXolT3M22J85QEiy_9jV0bHLkT8/edit?usp=sharing"

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 para que siempre traiga datos frescos y no use cache vieja
    return conn.read(spreadsheet=SHEET_URL, ttl=0)

def save_data(dataframe):
    conn.update(spreadsheet=SHEET_URL, data=dataframe)
    st.cache_data.clear() # Limpiar cache para forzar recarga

# --- INICIALIZACIÓN DE LA PLANILLA ---
df = load_data()

# Si la planilla está vacía o no tiene columnas, la inicializamos
if df.empty or "nombre" not in df.columns:
    st.info("Inicializando base de datos en Google Sheets...")
    columnas = [
        "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
        "residencia", "grupo_familiar", "monto_sugerido", "estado", 
        "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
    ]
    seed_data = [
        {
            "id": 1, "nombre": "Jorge / Alex", "apellido": "Szuster", "telefono": "+54 9 11 5428-3546",
            "rubro": "Insumos Hospitalarios", "contexto": "Vende colchones, mucha plata.", 
            "residencia": "Chateau/Hacoaj", "grupo_familiar": "-", "monto_sugerido": 50000, 
            "estado": "1. Por contactar", "monto_confirmado": 0, "proximos_pasos": "Llamar semana proxima",
            "responsable": "Equipo General", "fecha_registro": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "id": 2, "nombre": "Damian", "apellido": "Pasik / Julian Barki", "telefono": "1165390030",
            "rubro": "Instructor de Tiro", "contexto": "Nota: Cinthia.", 
            "residencia": "-", "grupo_familiar": "-", "monto_sugerido": 10000, 
            "estado": "1. Por contactar", "monto_confirmado": 0, "proximos_pasos": "-",
            "responsable": "Equipo General", "fecha_registro": datetime.now().strftime("%Y-%m-%d")
        }
    ]
    df = pd.DataFrame(seed_data, columns=columnas)
    save_data(df)
    st.rerun()

# --- CONFIGURACIÓN DE NEGOCIO ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]
LISTA_RESPONSABLES = ["Equipo General", "Julian Barki", "Ariel Goldman", "Responsable Externo"]
META_PROYECTO = 500000.0

# --- INTERFAZ ---
st.sidebar.title("🛡️ CRM Live")
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo"])

# --- DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Estado de Recaudación en Tiempo Real")
    
    # Asegurar que los montos sean números para calcular
    df['monto_confirmado'] = pd.to_numeric(df['monto_confirmado'], errors='coerce').fillna(0)
    df['monto_sugerido'] = pd.to_numeric(df['monto_sugerido'], errors='coerce').fillna(0)
    
    recaudado = df['monto_confirmado'].sum()
    proyectado = recaudado + df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PROYECTADO", f"USD {proyectado:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, META_PROYECTO - recaudado):,.0f}")
    c4.metric("CONTACTOS", len(df))

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=recaudado,
            delta={'reference': proyectado, 'position': "top", 'increasing': {'color': "blue"}},
            gauge={'axis': {'range': [None, META_PROYECTO]}, 'bar': {'color': "#2ecc71"}},
            title={'text': "Progreso vs Meta"}))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        resp_money = df.groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        st.plotly_chart(px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', title="USD por Responsable"), use_container_width=True)

# --- PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Gestión de Pipeline")
    
    busqueda = st.text_input("🔍 Buscar por Nombre, Rubro, Notas...")
    df_f = df[df.apply(lambda r: busqueda.lower() in str(r).lower(), axis=1)]

    for index, row in df_f.iterrows():
        color = "🔵" if "1." in str(row['estado']) else "🟢" if "6." in str(row['estado']) else "🟡"
        with st.expander(f"{color} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            
            c_h1, c_h2 = st.columns([2, 1])
            with c_h1:
                st.markdown(f"💰 **Sugerido:** USD {row['monto_sugerido']:,.0f} | **Confirmado:** :green[USD {row['monto_confirmado']:,.0f}]")
            with c_h2:
                edit_mode = st.toggle("✏️ Modo Edición", key=f"tog_{index}")

            if not edit_mode:
                st.markdown("---")
                col_izq, col_der = st.columns(2)
                with col_izq:
                    st.write(f"**📞 Tel:** {row['telefono']}")
                    st.write(f"**💼 Rubro:** {row['rubro']}")
                    st.write(f"**🏠 Residencia:** {row['residencia']}")
                    st.write(f"**👨‍👩‍👧 Familia:** {row['grupo_familiar']}")
                with col_der:
                    st.write(f"**📓 Contexto:** {row['contexto']}")
                    st.write(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_{index}"):
                    f1, f2, f3 = st.columns(3)
                    un_nom = f1.text_input("Nombre", row['nombre'])
                    un_ape = f2.text_input("Apellido", row['apellido'])
                    un_resp = f3.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                    
                    un_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    un_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                    un_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                    
                    un_tel = f1.text_input("Teléfono", row['telefono'])
                    un_res = f2.text_input("Residencia", row['residencia'])
                    un_fam = f3.text_input("Familia", row['grupo_familiar'])
                    un_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    un_ctx = st.text_area("Contexto", row['contexto'])
                    
                    if st.form_submit_button("✅ GUARDAR CAMBIOS"):
                        # Actualizar el DataFrame localmente
                        df.loc[index] = [
                            row['id'], un_nom, un_ape, un_tel, un_rub, un_ctx, 
                            un_res, un_fam, un_sug, un_est, un_conf, un_pas, un_resp, row['fecha_registro']
                        ]
                        save_data(df)
                        st.success("Guardado en Google Sheets!")
                        st.rerun()
                
                if st.button("🗑️ Eliminar Donante", key=f"del_{index}"):
                    df = df.drop(index)
                    save_data(df)
                    st.rerun()

# --- NUEVO ---
elif menu == "🆕 Registrar Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("nuevo_prospecto"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        resp = c1.selectbox("Responsable", LISTA_RESPONSABLES)
        rub = c2.text_input("Rubro")
        sug = c1.number_input("Monto Sugerido", value=0.0)
        ctx = st.text_area("Notas de contexto")
        
        if st.form_submit_button("🚀 Crear y Guardar"):
            if n:
                new_data = {
                    "id": len(df) + 1, "nombre": n, "apellido": a, "telefono": "", "rubro": rub,
                    "contexto": ctx, "residencia": "", "grupo_familiar": "", 
                    "monto_sugerido": sug, "estado": "1. Por contactar", "monto_confirmado": 0,
                    "proximos_pasos": "", "responsable": resp, 
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(df)
                st.success("Donante registrado en la nube!")
            else:
                st.error("El nombre es obligatorio.")
