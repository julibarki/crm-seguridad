import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Enterprise", layout="wide", page_icon="🛡️")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURACIÓN DE NEGOCIO ---
LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- MOTOR DE DATOS (VERSION SEGURA) ---
def load_data_from_cloud():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        
        # Casting de tipos para evitar errores de Pandas
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        text_cols = ["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "estado", "proximos_pasos", "responsable", "fecha_registro"]
        for col in text_cols:
            if col in data.columns:
                data[col] = data[col].astype(str).replace("nan", "-").replace("None", "-")
        
        return data
    except Exception:
        return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])

def save_to_cloud(dataframe):
    try:
        # Integridad: Solo estado 6 tiene monto real
        dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        df_to_save = dataframe.astype(str)
        conn.update(data=df_to_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- CARGA ---
df = load_data_from_cloud()

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta Objetivo (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline", "🆕 Nuevo"])

if st.sidebar.button("🔄 Sincronizar Ahora"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Estado de Recaudación")
    
    recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
    negoc = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()) if not df.empty else 0
    proyectado = recaudado + negoc
    
    c1, c2, c3 = st.columns(3)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PROYECTADO (Pipeline)", f"USD {proyectado:,.0f}")
    c3.metric("TOTAL CONTACTOS", len(df))

    col_gauge, col_tabla = st.columns([1, 1])
    
    with col_gauge:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = recaudado,
            gauge = {'axis': {'range': [None, meta_usd]}, 'bar': {'color': "#2ecc71"}},
            title = {'text': "Progreso hacia la Meta"}
        ))
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col_tabla:
        st.subheader("🏆 Donaciones Confirmadas")
        # Filtrar solo confirmados y mostrar columnas clave
        df_confirmados = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado']].sort_values(by='monto_confirmado', ascending=False)
        
        if not df_confirmados.empty:
            st.dataframe(
                df_confirmados,
                column_config={
                    "nombre": "Nombre",
                    "apellido": "Apellido",
                    "monto_confirmado": st.column_config.NumberColumn("Monto (USD)", format="$ %.2f")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aún no hay donaciones confirmadas en esta campaña.")

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline":
    st.title("Gestión de Pipeline")
    search = st.text_input("🔍 Buscar...").lower()
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df

    for idx, row in df_f.iterrows():
        emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
        with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            
            is_edit = st.toggle("✏️ Editar", key=f"ed_{row['id']}")
            if not is_edit:
                v1, v2 = st.columns(2)
                v1.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                v1.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                v2.write(f"📓 **Contexto:** {row['contexto']}")
                v2.write(f"🚀 **Paso:** {row['proximos_pasos']}")
            else:
                with st.form(key=f"f_edit_{row['id']}"):
                    f1, f2, f3 = st.columns(3)
                    u_nom = f1.text_input("Nombre", row['nombre'])
                    u_ape = f2.text_input("Apellido", row['apellido'])
                    u_tel = f3.text_input("Teléfono", row['telefono'])
                    idx_resp = LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0
                    u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=idx_resp)
                    u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    u_rub = f3.text_input("Rubro", row['rubro'])
                    u_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido']))
                    u_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado']))
                    u_res = f3.text_input("Residencia", row['residencia'])
                    u_fam = f1.text_input("Familia", row['grupo_familiar'])
                    u_pas = f2.text_input("Próximo Paso", row['proximos_pasos'])
                    u_ctx = st.text_area("Contexto", row['contexto'])
                    
                    if st.form_submit_button("💾 GUARDAR"):
                        df.at[idx, 'nombre'] = u_nom
                        df.at[idx, 'apellido'] = u_ape
                        df.at[idx, 'telefono'] = u_tel
                        df.at[idx, 'responsable'] = u_resp
                        df.at[idx, 'estado'] = u_est
                        df.at[idx, 'rubro'] = u_rub
                        df.at[idx, 'monto_sugerido'] = u_sug
                        df.at[idx, 'monto_confirmado'] = u_conf
                        df.at[idx, 'residencia'] = u_res
                        df.at[idx, 'grupo_familiar'] = u_fam
                        df.at[idx, 'proximos_pasos'] = u_pas
                        df.at[idx, 'contexto'] = u_ctx
                        if save_to_cloud(df): st.rerun()
                if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                    df = df.drop(idx)
                    if save_to_cloud(df): st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("n_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES)
        s = c2.number_input("Monto Sugerido (USD)", value=0.0)
        ctx = st.text_area("Notas de contexto")
        if st.form_submit_button("🚀 Crear"):
            if n:
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([{"id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"), "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-" }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_to_cloud(updated_df): st.success(f"¡{n} registrado!"); st.rerun()
