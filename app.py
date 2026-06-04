import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Elite", layout="wide", page_icon="🛡️")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        
        # LIMPIEZA CRÍTICA: Asegurar que los montos sean números reales
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        return data
    except Exception:
        return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])

def save_data(dataframe):
    # Regla de Integridad Financiera
    dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
    # Convertir a string para evitar líos de formato en GSheets
    dataframe_to_save = dataframe.astype(str)
    conn.update(data=dataframe_to_save)
    st.cache_data.clear()

# --- CONSTANTES ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- INICIALIZACIÓN ---
df = load_data()
responsables_existentes = sorted(df['responsable'].unique().tolist()) if not df.empty else ["Equipo General"]
if "Equipo General" not in responsables_existentes: responsables_existentes = ["Equipo General"] + responsables_existentes

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta Objetivo (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline", "🆕 Nuevo"])

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Análisis de Recaudación")
    
    # Cálculos seguros (forzando float)
    conf_real = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
    negoc = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum())
    proyectado = conf_real + negoc
    perdido = float(df[df['estado'] == "7. Rechazó"]['monto_sugerido'].sum())
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO", f"USD {conf_real:,.0f}")
    c2.metric("POTENCIAL", f"USD {negoc:,.0f}")
    c3.metric("PROYECTADO TOTAL", f"USD {proyectado:,.0f}")
    c4.metric("PERDIDO (RECHAZOS)", f"USD {perdido:,.0f}")

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    
    with col_a:
        # Gauge simplificado para máxima compatibilidad
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = conf_real,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"Progreso Real (Meta {meta_usd:,.0f})"},
            gauge = {
                'axis': {'range': [None, meta_usd]},
                'bar': {'color': "#2ecc71"},
                'steps': [{'range': [0, proyectado], 'color': "#ebf5fb"}] # Sombra azul para el proyectado
            }
        ))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        st.subheader("Efectividad")
        counts = df['estado'].value_counts().reindex(ESTADOS, fill_value=0).reset_index()
        counts.columns = ['Estado', 'Cant']
        st.plotly_chart(px.bar(counts, x='Cant', y='Estado', orientation='h', color='Estado'), use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline":
    st.title("Gestión de Pipeline")
    search = st.text_input("🔍 Buscar (Nombre, Rubro, Notas...)").lower()
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)]

    for index, row in df_f.iterrows():
        alerta = "⚠️" if (float(row['monto_confirmado']) > 0 and row['estado'] != "6. Donación Confirmada") else ""
        emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
        
        with st.expander(f"{alerta} {emoji} {row['nombre']} {row['apellido']} | {row['estado']}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            with c2:
                col_btn1, col_btn2, edit_tog = st.columns(3)
                if col_btn1.button("✅", key=f"c_{index}"):
                    df.at[index, 'estado'] = '6. Donación Confirmada'; save_data(df); st.rerun()
                if col_btn2.button("❌", key=f"r_{index}"):
                    df.at[index, 'estado'] = '7. Rechazó'; df.at[index, 'monto_confirmado'] = 0; save_data(df); st.rerun()
                is_edit = edit_tog.toggle("✏️", key=f"e_{index}")

            if not is_edit:
                st.markdown("---")
                v1, v2 = st.columns(2)
                v1.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                v1.write(f"🏠 **Residencia:** {row['residencia']} | 👨‍👩‍👧 **Familia:** {row['grupo_familiar']}")
                v2.write(f"📓 **Contexto:** {row['contexto']}")
                v2.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"f_{index}"):
                    f1, f2, f3 = st.columns(3)
                    u_nom = f1.text_input("Nombre", row['nombre'])
                    u_ape = f2.text_input("Apellido", row['apellido'])
                    u_tel = f3.text_input("Teléfono", row['telefono'])
                    u_resp = f1.selectbox("Responsable", responsables_existentes, index=responsables_existentes.index(row['responsable']) if row['responsable'] in responsables_existentes else 0)
                    u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    u_sug = f3.number_input("Sugerido", value=float(row['monto_sugerido']))
                    u_conf = f1.number_input("Confirmado", value=float(row['monto_confirmado']))
                    u_res = f2.text_input("Residencia", row['residencia'])
                    u_fam = f3.text_input("Familia", row['grupo_familiar'])
                    u_rub = f1.text_input("Rubro", row['rubro'])
                    u_ctx = st.text_area("Contexto", row['contexto'])
                    u_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    if st.form_submit_button("💾 GUARDAR"):
                        df.loc[index] = [row['id'], u_nom, u_ape, u_tel, u_rub, u_ctx, u_res, u_fam, u_sug, u_est, u_conf, u_pas, u_resp, row['fecha_registro']]
                        save_data(df); st.rerun()
                if st.button("🗑️ ELIMINAR", key=f"del_{index}"):
                    df = df.drop(index); save_data(df); st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("n"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Responsable", responsables_existentes)
        s = c2.number_input("Sugerido (USD)", value=0.0)
        if st.form_submit_button("Crear"):
            if n:
                new = pd.DataFrame([{"id": str(len(df)+1), "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0, "fecha_registro": datetime.now().strftime("%Y-%m-%d")}]).fillna("-")
                df = pd.concat([df, new], ignore_index=True); save_data(df); st.rerun()
