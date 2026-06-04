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

# --- MOTOR DE DATOS (PROTECCIÓN TOTAL CONTRA ERRORES DE TIPO) ---
def load_data():
    try:
        # Forzar lectura sin caché
        data = conn.read(ttl=0)
        
        if data is None or data.empty:
            return pd.DataFrame()

        # 1. Limpieza de nombres de columnas
        data.columns = [str(c).strip() for c in data.columns]
        
        # 2. Sanitización de Números (Montos)
        for col in ['monto_confirmado', 'monto_sugerido']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
            else:
                data[col] = 0.0
        
        # 3. Sanitización de Texto (FIX: Evita el error 'float object has no attribute endswith')
        for col in data.columns:
            if col not in ['monto_confirmado', 'monto_sugerido']:
                # Convertimos todo a string primero, manejando nulos
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
                # Limpiamos el ".0" usando regex (más seguro que endswith)
                data[col] = data[col].str.replace(r'\.0$', '', regex=True)
        
        return data
    except Exception as e:
        st.error(f"Error técnico al leer Excel: {e}")
        return pd.DataFrame()

def save_data(dataframe):
    try:
        # Integridad: Solo estado 6 tiene monto real
        if 'estado' in dataframe.columns and 'monto_confirmado' in dataframe.columns:
            dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        
        # Guardamos todo como string para evitar errores de celda en Google Sheets
        df_save = dataframe.astype(str)
        conn.update(data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- CARGA ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ Recaudación Pro")
meta_usd = st.sidebar.number_input("Meta Global (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline Operativo", "🆕 Nuevo Registro"])

if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Panel de Control Estratégico")
    
    if df.empty or "nombre" not in df.columns:
        st.warning("Crea tu primer registro en 'Nuevo Registro' para activar el Dashboard.")
    else:
        # Cálculos
        recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
        pipeline_val = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum())
        faltante = max(0, meta_usd - recaudado)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
        c2.metric("POTENCIAL PIPELINE", f"USD {pipeline_val:,.0f}")
        c3.metric("FALTANTE META", f"USD {faltante:,.0f}")
        c4.metric("TOTAL CONTACTOS", len(df))

        st.markdown("---")
        
        col_left, col_right = st.columns([1, 1.2])
        
        with col_left:
            # Gauge Pro
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = recaudado,
                gauge = {
                    'axis': {'range': [0, meta_usd]},
                    'bar': {'color': "#2ecc71"},
                    'bgcolor': "rgba(0,0,0,0)",
                    'steps': [{'range': [0, meta_usd], 'color': "rgba(200, 200, 200, 0.2)"}],
                },
                title = {'text': "Avance vs Meta", 'font': {'size': 20}}
            ))
            fig_gauge.update_layout(height=350, margin=dict(l=60, r=60, t=60, b=40), paper_bgcolor='rgba(0,0,0,0)', font={'color': "#f8f9fa"})
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            st.subheader("🏆 Donaciones Confirmadas")
            df_conf = df[df['estado'] == "6. Donación Confirmada"][['nombre', 'apellido', 'monto_confirmado']].sort_values(by='monto_confirmado', ascending=False)
            st.dataframe(df_conf, column_config={"monto_confirmado": st.column_config.NumberColumn("USD", format="$ %.0f")}, use_container_width=True, hide_index=True)

        with col_right:
            st.subheader("Análisis por Rubro")
            rubro_data = df[df['estado'] == "6. Donación Confirmada"].groupby('rubro')['monto_confirmado'].sum().reset_index()
            if not rubro_data.empty:
                fig_rubro = px.pie(rubro_data, values='monto_confirmado', names='rubro', hole=0.4)
                fig_rubro.update_layout(margin=dict(t=30, b=20, l=20, r=20), height=300, paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_rubro, use_container_width=True)
            
            st.subheader("USD por Responsable")
            resp_data = df[df['estado'] == "6. Donación Confirmada"].groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
            fig_resp = px.bar(resp_data, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db'])
            fig_resp.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_resp, use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline Operativo":
    st.title("Gestión de Prospectos")
    
    if df.empty:
        st.info("La base de datos está vacía.")
    else:
        st.write(f"📂 **{len(df)}** registros en la nube.")
        search = st.text_input("🔍 Buscar...").lower()
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)] if search else df

        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                
                is_edit = st.toggle("✏️ Editar", key=f"ed_{row.get('id', idx)}")
                
                if not is_edit:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"📞 **Tel:** {row['telefono']}")
                        st.write(f"💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                    with c2:
                        st.write(f"📓 **Contexto:** {row['contexto']}")
                        st.write(f"🚀 **Paso:** {row['proximos_pasos']}")
                else:
                    with st.form(key=f"f_edit_{row.get('id', idx)}"):
                        f1, f2, f3 = st.columns(3)
                        u_nom = f1.text_input("Nombre", row['nombre'])
                        u_ape = f2.text_input("Apellido", row['apellido'])
                        u_tel = f3.text_input("Teléfono", row['telefono'])
                        u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                        u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                        u_sug = f3.number_input("Sugerido", value=float(row['monto_sugerido']))
                        u_conf = f1.number_input("Confirmado", value=float(row['monto_confirmado']))
                        u_res = f2.text_input("Residencia", row['residencia'])
                        u_fam = f3.text_input("Familia", row['grupo_familiar'])
                        u_rub = f1.text_input("Rubro", row['rubro'])
                        u_ctx = st.text_area("Contexto", row['contexto'])
                        u_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                        
                        if st.form_submit_button("💾 GUARDAR"):
                            target_id = str(row['id'])
                            mask = df['id'] == target_id
                            df.loc[mask, ['nombre', 'apellido', 'responsable', 'estado', 'monto_sugerido', 'monto_confirmado', 'telefono', 'residencia', 'grupo_familiar', 'rubro', 'contexto', 'proximos_pasos']] = [
                                u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_ctx, u_pas
                            ]
                            if save_data(df): st.rerun()
                    
                    if st.button("🗑️ ELIMINAR DONANTE", key=f"del_{row.get('id', idx)}"):
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
