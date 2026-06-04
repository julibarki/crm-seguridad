import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Elite v3.0", layout="wide", page_icon="🛡️")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURACIÓN DE NEGOCIO ---
LISTA_RESPONSABLES = ["Equipo General", "Avir", "Asher", "Kamer", "Jesef", "Adan", "Itza", "Kaleb", "Wyatt"]
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- MOTOR DE DATOS ---
def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        data = data.fillna("-")
        return data
    except:
        return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])

def save_data(dataframe):
    try:
        # Regla de Integridad: Solo estado 6 tiene monto
        dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        df_save = dataframe.astype(str)
        conn.update(data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error de red: {e}")
        return False

# --- CARGA ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ Recaudación Pro")
meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline Operativo", "🆕 Nuevo Registro"])
if st.sidebar.button("🔄 Sincronizar Nube"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Panel de Control y Toma de Decisiones")
    
    # KPIs Rápidos
    recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
    pipeline_val = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum())
    faltante = max(0, meta_usd - recaudado)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PIPELINE CALIENTE", f"USD {pipeline_val:,.0f}")
    c3.metric("FALTANTE META", f"USD {faltante:,.0f}")
    c4.metric("CONTACTOS", len(df))

    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1.2])
    
    with col_left:
        # Gráfico de Aguja
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = recaudado,
            gauge = {'axis': {'range': [None, meta_usd]}, 'bar': {'color': "#2ecc71"}},
            title = {'text': "Progreso vs Meta (USD)"}
        ))
        fig_gauge.update_layout(height=300, margin=dict(t=0, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.subheader("🏆 Donaciones Confirmadas")
        df_conf = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado']].sort_values(by='monto_confirmado', ascending=False)
        st.dataframe(df_conf, column_config={"monto_confirmado": st.column_config.NumberColumn("USD", format="$ %.0f")}, use_container_width=True, hide_index=True)

    with col_right:
        # Business Intelligence: Recaudación por Rubro
        st.subheader("Análisis por Rubro")
        rubro_data = df[df['estado'] == "6. Donación Confirmada"].groupby('rubro')['monto_confirmado'].sum().reset_index()
        if not rubro_data.empty:
            fig_rubro = px.pie(rubro_data, values='monto_confirmado', names='rubro', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_rubro, use_container_width=True)
        else:
            st.info("No hay datos de recaudación por rubro todavía.")
        
        # Ranking de Responsables
        st.subheader("Recaudación por Responsable")
        resp_data = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        st.plotly_chart(px.bar(resp_data, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db']), use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline Operativo":
    st.title("Gestión de Prospectos")
    search = st.text_input("🔍 Buscar por Nombre, Rubro, Notas, Familia o Responsable...").lower()
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df

    for idx, row in df_f.iterrows():
        emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
        with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            
            # Sub-header Financiero
            st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            
            is_edit = st.toggle("✏️ Abrir Edición", key=f"ed_{row['id']}")
            
            if not is_edit:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                    st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                with c2:
                    st.write(f"📓 **Contexto:** {row['contexto']}")
                    st.write(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_{row['id']}"):
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
                    u_ctx = st.text_area("Contexto/Notas", row['contexto'])
                    
                    if st.form_submit_button("💾 ACTUALIZAR"):
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
                        if save_data(df): st.rerun()
                
                if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                    df = df.drop(idx)
                    if save_data(df): st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Nuevo Registro":
    st.subheader("Cargar Nuevo Prospecto")
    with st.form("n_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Responsable", LISTA_RESPONSABLES)
        s = c2.number_input("Sugerido (USD)", value=0.0)
        ctx = st.text_area("Notas de contexto inicial")
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([{
                    "id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, 
                    "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                    "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_data(updated_df): st.success(f"¡{n} registrado exitosamente!"); st.rerun()
