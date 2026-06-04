import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Enterprise", layout="wide", page_icon="🛡️")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            raise ValueError("Vacío")
        # Asegurar tipos de datos numéricos
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
    # Convertimos todo a string para evitar conflictos de formato en la planilla
    dataframe_to_save = dataframe.astype(str)
    conn.update(data=dataframe_to_save)
    st.cache_data.clear()

# --- CONSTANTES DE NEGOCIO ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]
LISTA_RESPONSABLES = ["Equipo General", "Julian Barki", "Ariel Goldman", "Responsable Externo"]

# --- INICIALIZACIÓN ---
df = load_data()

if df.empty or "nombre" not in df.columns:
    st.info("Inicializando estructura en Google Sheets...")
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

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_objetivo = st.sidebar.number_input("Meta del Proyecto (USD)", value=500000, step=10000)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo"])

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Panel de Control Estratégico")
    
    recaudado = df['monto_confirmado'].sum()
    proyectado = recaudado + df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()
    total_contactos = len(df)
    contactados = len(df[df['estado'] != "1. Por contactar"])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PROYECTADO (Pipeline)", f"USD {proyectado:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, meta_objetivo - recaudado):,.0f}")
    c4.metric("AVANCE GESTIÓN", f"{contactados}/{total_contactos}")

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    
    with col_a:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta", value = recaudado,
            delta = {'reference': proyectado, 'position': "top", 'increasing': {'color': "blue"}},
            gauge = {'axis': {'range': [None, meta_objetivo]}, 'bar': {'color': "#2ecc71"}},
            title = {'text': "Progreso Real vs Proyectado"}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col_b:
        st.subheader("USD por Responsable")
        resp_money = df.groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        fig_resp = px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db'])
        st.plotly_chart(fig_resp, use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Pipeline de Donantes")
    col_f1, col_f2 = st.columns([3, 1])
    search = col_f1.text_input("🔍 Buscar (Nombre, Rubro, Notas, Familia...)")
    f_resp = col_f2.selectbox("Filtrar Encargado", ["Todos"] + LISTA_RESPONSABLES)
    
    df_f = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    if f_resp != "Todos": df_f = df_f[df_f['responsable'] == f_resp]

    for index, row in df_f.iterrows():
        emoji = "🔵" if "1." in str(row['estado']) else "🟢" if "6." in str(row['estado']) else "🟡"
        with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            
            c_header_1, c_header_2 = st.columns([2, 1])
            with c_header_1:
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            with c_header_2:
                # Acciones rápidas
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                if col_btn1.button("✅ Conf.", key=f"q_c_{index}"):
                    df.at[index, 'estado'] = '6. Donación Confirmada'
                    save_data(df); st.rerun()
                if col_btn2.button("❌ Rech.", key=f"q_r_{index}"):
                    df.at[index, 'estado'] = '7. Rechazó'
                    save_data(df); st.rerun()
                edit_mode = col_btn3.toggle("✏️", key=f"tog_{index}")

            if not edit_mode:
                st.markdown("---")
                col_izq, col_der = st.columns(2)
                with col_izq:
                    st.markdown(f"**📞 Tel:** {row['telefono']}")
                    st.markdown(f"**💼 Rubro:** {row['rubro']}")
                    st.markdown(f"**🏠 Residencia:** {row['residencia']}")
                    st.markdown(f"**👨‍👩‍👧 Familia:** {row['grupo_familiar']}")
                with col_der:
                    st.markdown(f"**📓 Contexto:** {row['contexto']}")
                    st.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_ed_{index}"):
                    f1, f2, f3 = st.columns(3)
                    un_nom = f1.text_input("Nombre", row['nombre'])
                    un_ape = f2.text_input("Apellido", row['apellido'])
                    un_tel = f3.text_input("Teléfono", row['telefono'])
                    un_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                    un_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    un_rub = f3.text_input("Rubro", row['rubro'])
                    un_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido']))
                    un_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado']))
                    un_res = f3.text_input("Residencia", row['residencia'])
                    un_fam = f1.text_input("Familia", row['grupo_familiar'])
                    un_ctx = st.text_area("Contexto", row['contexto'])
                    un_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    
                    if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df.loc[index] = [row['id'], un_nom, un_ape, un_tel, un_rub, un_ctx, un_res, un_fam, un_sug, un_est, un_conf, un_pas, un_resp, row['fecha_registro']]
                        save_data(df); st.rerun()
                
                if st.button("🗑️ ELIMINAR", key=f"del_{index}"):
                    df = df.drop(index); save_data(df); st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Registrar Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("nuevo_prospecto"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        resp = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES)
        rub = c2.text_input("Rubro")
        sug = c1.number_input("Monto Sugerido", value=0.0)
        ctx = st.text_area("Notas de contexto")
        
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                new_data = pd.DataFrame([{
                    "id": str(len(df) + 1), "nombre": n, "apellido": a, "telefono": "-", "rubro": rub,
                    "contexto": ctx, "residencia": "-", "grupo_familiar": "-", 
                    "monto_sugerido": str(sug), "estado": "1. Por contactar", "monto_confirmado": "0",
                    "proximos_pasos": "-", "responsable": resp, 
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df); st.success("Registrado en la nube!")
            else:
                st.error("El nombre es obligatorio.")
