import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Elite", layout="wide", page_icon="🛡️")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURACIÓN DE NEGOCIO ---
LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- MOTOR DE DATOS (PROTECCIÓN DE TIPOS PANDAS 3.0) ---
def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        
        # 1. Forzar montos a numérico (float)
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        # 2. Forzar TODO lo demás a String para evitar el TypeError
        for col in data.columns:
            if col not in ['monto_confirmado', 'monto_sugerido']:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
        
        return data
    except Exception:
        return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])

def save_data(dataframe):
    try:
        # Integridad: Si no es confirmado, el monto es 0
        dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        # Guardamos todo como string en GSheets para evitar conflictos de celda
        df_save = dataframe.astype(str)
        conn.update(data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error de red: {e}")
        return False

# --- CARGA INICIAL ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ Recaudación Pro")
meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline Operativo", "🆕 Nuevo Registro"])
if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear()
    st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Panel de Control")
    recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
    pipeline_val = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum())
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PIPELINE CALIENTE", f"USD {pipeline_val:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, meta_usd - recaudado):,.0f}")
    c4.metric("TOTAL CONTACTOS", len(df))

    st.markdown("---")
    col_left, col_right = st.columns([1, 1.2])
    
    with col_left:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = recaudado,
            gauge = {
                'axis': {'range': [0, meta_usd]},
                'bar': {'color': "#2ecc71"},
                'bgcolor': "rgba(0,0,0,0)",
                'steps': [{'range': [0, meta_usd], 'color': "rgba(200, 200, 200, 0.2)"}],
            },
            title = {'text': "Avance vs Meta (USD)"}
        ))
        fig_gauge.update_layout(height=380, margin=dict(l=60, r=60, t=80, b=40), paper_bgcolor='rgba(0,0,0,0)', font={'color': "#f8f9fa"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.subheader("🏆 Donaciones Confirmadas")
        df_conf = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado']].sort_values(by='monto_confirmado', ascending=False)
        st.dataframe(df_conf, column_config={"monto_confirmado": st.column_config.NumberColumn("USD", format="$ %.0f")}, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("USD por Responsable")
        resp_data = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        fig_resp = px.bar(resp_data, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db'])
        fig_resp.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_resp, use_container_width=True)

# --- PIPELINE ---
elif menu == "👥 Pipeline Operativo":
    st.title("Gestión de Prospectos")
    search = st.text_input("🔍 Buscar...").lower()
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df

    for idx, row in df_f.iterrows():
        emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
        with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            is_edit = st.toggle("✏️ Editar", key=f"ed_{row['id']}")
            
            if not is_edit:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                    st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                with c2:
                    st.write(f"📓 **Contexto:** {row['contexto']}")
                    st.write(f"🚀 **Paso:** {row['proximos_pasos']}")
            else:
                with st.form(key=f"f_{row['id']}"):
                    f1, f2, f3 = st.columns(3)
                    u_nom = f1.text_input("Nombre", row['nombre'])
                    u_ape = f2.text_input("Apellido", row['apellido'])
                    u_resp = f3.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                    u_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    u_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                    u_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                    u_tel = f1.text_input("Teléfono", row['telefono'])
                    u_res = f2.text_input("Residencia", row['residencia'])
                    u_fam = f3.text_input("Familia", row['grupo_familiar'])
                    u_rub = f1.text_input("Rubro", row['rubro'])
                    u_ctx = st.text_area("Contexto", row['contexto'])
                    u_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    
                    if st.form_submit_button("💾 GUARDAR"):
                        # ACTUALIZACIÓN SEGURA POR ID
                        target_id = str(row['id'])
                        # Localizar la fila real en el DataFrame principal por ID
                        df.loc[df['id'] == target_id, ['nombre', 'apellido', 'responsable', 'estado', 'monto_sugerido', 'monto_confirmado', 'telefono', 'residencia', 'grupo_familiar', 'rubro', 'contexto', 'proximos_pasos']] = [
                            u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_ctx, u_pas
                        ]
                        if save_data(df): st.rerun()
                
                if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                    df = df[df['id'] != str(row['id'])]
                    if save_data(df): st.rerun()

# --- NUEVO ---
elif menu == "🆕 Nuevo Registro":
    st.subheader("Cargar Nuevo Prospecto")
    with st.form("n_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Responsable", LISTA_RESPONSABLES)
        s = c2.number_input("Sugerido (USD)", value=0.0)
        ctx = st.text_area("Notas de contexto")
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([{
                    "id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, 
                    "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                    "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_data(updated_df): st.success(f"¡{n} registrado!"); st.rerun()
