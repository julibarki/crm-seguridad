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

# --- MOTOR DE DATOS (PROTECCIÓN ELITE) ---
def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        
        # 1. Limpieza de columnas
        data.columns = [str(c).strip() for c in data.columns]
        
        # 2. Sanitización Numérica
        for col in ['monto_confirmado', 'monto_sugerido']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        # 3. Sanitización de Texto y Limpieza de ".0" (Regex Blindado)
        for col in data.columns:
            if col not in ['monto_confirmado', 'monto_sugerido']:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
                data[col] = data[col].str.replace(r'\.0$', '', regex=True)
        
        return data
    except Exception:
        return pd.DataFrame()

def save_data(dataframe):
    try:
        # Regla de Oro: Solo estado 6 conserva monto confirmado
        if 'estado' in dataframe.columns and 'monto_confirmado' in dataframe.columns:
            dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        
        # Guardado seguro como String
        df_save = dataframe.astype(str)
        conn.update(data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error de sincronización: {e}")
        return False

# --- CARGA ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Recaudación")
meta_usd = st.sidebar.number_input("Meta Global (USD)", value=24000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline Operativo", "🆕 Nuevo Registro"])
if st.sidebar.button("🔄 Sincronizar Ahora"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Panel de Control de Recaudación")
    
    if df.empty or "nombre" not in df.columns:
        st.warning("No hay registros en la base de datos.")
    else:
        # Métricas Core
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
        pipeline_negoc = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum())
        faltante = max(0, meta_usd - recaudado)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("EN PIPELINE", f"USD {pipeline_negoc:,.0f}")
        c3.metric("FALTANTE META", f"USD {faltante:,.0f}")
        c4.metric("TOTAL CONTACTOS", len(df))

        st.markdown("---")
        
        col_gauge, col_stats = st.columns([1, 1.2])
        
        with col_gauge:
            # Gauge Refinado
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = recaudado,
                gauge = {
                    'axis': {'range': [0, meta_usd], 'tickformat': '.0s'},
                    'bar': {'color': "#2ecc71"},
                    'bgcolor': "rgba(0,0,0,0)",
                    'steps': [{'range': [0, meta_usd], 'color': "rgba(200,200,200,0.1)"}],
                    'borderwidth': 1
                },
                title = {'text': "Avance hacia la Meta", 'font': {'size': 18}}
            ))
            fig_gauge.update_layout(height=350, margin=dict(l=60, r=60, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "#f8f9fa"})
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_stats:
            st.subheader("📊 Ranking por Responsable")
            # Ranking de dinero real traído por cada uno
            resp_data = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
            if not resp_data.empty:
                fig_resp = px.bar(resp_data, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db'], labels={'monto_confirmado':'USD Confirmados', 'responsable':''})
                fig_resp.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_resp, use_container_width=True)
            else:
                st.info("Aún no hay recaudación confirmada por responsables.")

        st.markdown("---")
        st.subheader("🏆 Tabla de Honor (Donaciones Confirmadas)")
        df_conf = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado', 'responsable']].sort_values(by='monto_confirmado', ascending=False)
        if not df_conf.empty:
            st.dataframe(df_conf, column_config={
                "nombre": "Nombre", "apellido": "Apellido", "responsable": "Encargado",
                "monto_confirmado": st.column_config.NumberColumn("Monto USD", format="$ %.0f")
            }, use_container_width=True, hide_index=True)
        else:
            st.info("No hay donaciones confirmadas para mostrar.")

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline Operativo":
    st.title("Gestión de Prospectos")
    
    if df.empty:
        st.info("Base de datos vacía.")
    else:
        search = st.text_input("🔍 Buscar por Nombre, Notas, Responsable o Familia...").lower()
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df

        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                
                is_edit = st.toggle("✏️ Editar Registro", key=f"ed_{row['id']}")
                
                if not is_edit:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                    with c2:
                        st.write(f"📓 **Contexto:** {row['contexto']}")
                        st.write(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
                else:
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2, f3 = st.columns(3)
                        un_nom = f1.text_input("Nombre", row['nombre'])
                        un_ape = f2.text_input("Apellido", row['apellido'])
                        idx_resp = LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0
                        u_resp = f3.selectbox("Responsable", LISTA_RESPONSABLES, index=idx_resp)
                        
                        un_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                        un_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                        un_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                        
                        un_tel = f1.text_input("Teléfono", row['telefono'])
                        un_res = f2.text_input("Residencia", row['residencia'])
                        un_fam = f3.text_input("Familia", row['grupo_familiar'])
                        
                        un_rub = f1.text_input("Rubro", row['rubro'])
                        un_ctx = st.text_area("Contexto", row['contexto'])
                        un_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                        
                        if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                            target_id = str(row['id'])
                            mask = df['id'] == target_id
                            df.loc[mask, ['nombre', 'apellido', 'responsable', 'estado', 'monto_sugerido', 'monto_confirmado', 'telefono', 'residencia', 'grupo_familiar', 'rubro', 'contexto', 'proximos_pasos']] = [
                                un_nom, un_ape, u_resp, un_est, un_sug, un_conf, un_tel, un_res, un_fam, un_rub, un_ctx, un_pas
                            ]
                            if save_data(df): st.rerun()
                    
                    if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                        df = df[df['id'] != str(row['id'])]
                        if save_data(df): st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Nuevo Registro":
    st.subheader("Cargar Nuevo Prospecto")
    with st.form("n_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES)
        s = c2.number_input("Monto Sugerido (USD)", value=0.0)
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
