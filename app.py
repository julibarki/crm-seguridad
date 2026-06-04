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
COLUMNAS_BASE = ["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"]

# --- MOTOR DE DATOS ---
def load_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=COLUMNAS_BASE)
        
        # 1. Asegurar que existan todas las columnas
        for col in COLUMNAS_BASE:
            if col not in data.columns:
                data[col] = "-"
        
        # 2. Forzar montos a float
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        # 3. Limpieza de texto y quitar el ".0" de los teléfonos/IDs
        for col in data.columns:
            if col not in ['monto_confirmado', 'monto_sugerido']:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '-')
                data[col] = data[col].apply(lambda x: x[:-2] if x.endswith('.0') else x)
        
        return data[COLUMNAS_BASE] # Reordenar según estructura base
    except Exception:
        return pd.DataFrame(columns=COLUMNAS_BASE)

def save_data(dataframe):
    try:
        # Integridad: Solo el estado 6 tiene dinero real
        dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        df_save = dataframe.astype(str)
        conn.update(data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar en la nube: {e}")
        return False

# --- CARGA INICIAL ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta Objetivo (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline Operativo", "🆕 Nuevo"])

if st.sidebar.button("🔄 Sincronizar Ahora"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Panel de Control")
    recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("CONTACTOS", len(df))
    c3.metric("META", f"USD {meta_usd:,.0f}")

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = recaudado,
        gauge = {'axis': {'range': [0, meta_usd]}, 'bar': {'color': "#2ecc71"}, 'bgcolor': "rgba(0,0,0,0)"},
        title = {'text': "Avance Real"}
    ))
    fig_gauge.update_layout(height=350, margin=dict(l=60, r=60, t=80, b=40), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline Operativo":
    st.title("Gestión de Prospectos")
    
    st.write(f"📂 Base de datos: **{len(df)}** registros.")
    
    search = st.text_input("🔍 Buscar por cualquier campo...").lower()
    
    # Filtro de búsqueda ultra-robusto
    if search:
        # Convertimos la fila a un solo string largo para buscar sin errores de tipos
        df_f = df[df.apply(lambda row: search in " ".join(row.astype(str)).lower(), axis=1)]
    else:
        df_f = df

    if df_f.empty and len(df) > 0:
        st.warning("No hay resultados para esta búsqueda.")
    elif df.empty:
        st.info("La base de datos está vacía. Crea un donante en 'Nuevo'.")
    else:
        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                
                is_edit = st.toggle("✏️ Editar Ficha", key=f"ed_{row['id']}_{idx}")
                
                if not is_edit:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"📞 **Tel:** {row['telefono']} | 💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']} | 👨‍👩‍👧 **Fam:** {row['grupo_familiar']}")
                    with c2:
                        st.write(f"📓 **Contexto:** {row['contexto']}")
                        st.write(f"🚀 **Paso:** {row['proximos_pasos']}")
                else:
                    with st.form(key=f"f_edit_{row['id']}_{idx}"):
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
                        u_res = f1.text_input("Residencia", row['residencia'])
                        u_fam = f2.text_input("Familia", row['grupo_familiar'])
                        u_pas = f3.text_input("Próximo Paso", row['proximos_pasos'])
                        u_ctx = st.text_area("Contexto", row['contexto'])
                        
                        if st.form_submit_button("💾 GUARDAR"):
                            # Actualización por posición ID-Match
                            target_id = str(row['id'])
                            mask = df['id'] == target_id
                            df.loc[mask, ['nombre', 'apellido', 'responsable', 'estado', 'monto_sugerido', 'monto_confirmado', 'telefono', 'residencia', 'grupo_familiar', 'rubro', 'contexto', 'proximos_pasos']] = [
                                u_nom, u_ape, u_resp, u_est, u_sug, u_conf, u_tel, u_res, u_fam, u_rub, u_ctx, u_pas
                            ]
                            if save_data(df): st.rerun()
                    
                    if st.button("🗑️ ELIMINAR DONANTE", key=f"del_{row['id']}_{idx}"):
                        df = df[df['id'] != str(row['id'])]
                        if save_data(df): st.rerun()

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
        if st.form_submit_button("🚀 Crear y Guardar"):
            if n:
                new_id = str(int(datetime.now().timestamp()))
                new_row = pd.DataFrame([{
                    "id": new_id, "nombre": n, "apellido": a, "responsable": r, "monto_sugerido": s, 
                    "estado": "1. Por contactar", "monto_confirmado": 0.0, "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                    "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", "grupo_familiar": "-", "proximos_pasos": "-"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_data(updated_df): st.success(f"¡{n} registrado exitosamente!"); st.rerun()
