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

# --- MOTOR DE DATOS (REFACTORIZADO PARA TIEMPO REAL) ---
def load_data_from_cloud():
    try:
        # ttl=0 es clave para que no use memoria vieja
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])
        
        # Asegurar limpieza de datos
        for col in ['monto_confirmado', 'monto_sugerido']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)
        
        data['id'] = data['id'].astype(str)
        return data.fillna("-")
    except Exception:
        return pd.DataFrame(columns=["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"])

def save_to_cloud(dataframe):
    try:
        # Regla de Oro: Solo el estado 6 tiene dinero real
        dataframe.loc[dataframe['estado'] != "6. Donación Confirmada", 'monto_confirmado'] = 0
        
        # Convertir todo a texto para Google Sheets
        df_to_save = dataframe.astype(str)
        conn.update(data=df_to_save)
        
        # LIMPIEZA ABSOLUTA DE CACHÉ
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False

# --- CARGA CRÍTICA ---
df = load_data_from_cloud()

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta Objetivo (USD)", value=500000.0, step=10000.0)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👥 Pipeline", "🆕 Nuevo Registro"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Forzar Sincronización"):
    st.cache_data.clear()
    st.rerun()

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Estado de Recaudación")
    
    recaudado = float(df[df['estado'] == "6. Donación Confirmada"]['monto_confirmado'].sum()) if not df.empty else 0
    negociacion = float(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()) if not df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("POTENCIAL (Pipeline)", f"USD {negociacion:,.0f}")
    c3.metric("TOTAL CONTACTOS", len(df))

    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = recaudado,
        gauge = {'axis': {'range': [None, meta_usd]}, 'bar': {'color': "#2ecc71"}},
        title = {'text': "Progreso hacia la Meta"}
    ))
    st.plotly_chart(fig, use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline":
    st.title("Gestión de Seguimiento")
    
    st.write(f"📂 Total en base de datos: **{len(df)}** donantes.")
    
    search = st.text_input("🔍 Buscar por cualquier campo...").lower()
    
    # Lógica de filtrado robusta
    if search:
        df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)]
    else:
        df_f = df

    if df_f.empty:
        st.warning("No se encontraron donantes con ese criterio o la base está vacía.")
    else:
        for idx, row in df_f.iterrows():
            emoji = "🟢" if row['estado'] == "6. Donación Confirmada" else "🔴" if row['estado'] == "7. Rechazó" else "🟡"
            
            with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
                
                c_h1, c_h2 = st.columns([2, 1])
                with c_h1:
                    st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
                
                is_edit = st.toggle("✏️ Editar información", key=f"ed_{row['id']}")

                if not is_edit:
                    v1, v2 = st.columns(2)
                    with v1:
                        st.write(f"📞 **Tel:** {row['telefono']}")
                        st.write(f"💼 **Rubro:** {row['rubro']}")
                        st.write(f"🏠 **Resid:** {row['residencia']}")
                    with v2:
                        st.write(f"📓 **Contexto:** {row['contexto']}")
                        st.markdown(f"🚀 **Paso:** :orange[{row['proximos_pasos']}]")
                else:
                    with st.form(key=f"f_edit_{row['id']}"):
                        f1, f2, f3 = st.columns(3)
                        u_nom = f1.text_input("Nombre", row['nombre'])
                        u_ape = f2.text_input("Apellido", row['apellido'])
                        u_tel = f3.text_input("Teléfono", row['telefono'])
                        
                        u_resp = f1.selectbox("Responsable", LISTA_RESPONSABLES, index=LISTA_RESPONSABLES.index(row['responsable']) if row['responsable'] in LISTA_RESPONSABLES else 0)
                        u_est = f2.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                        u_rub = f3.text_input("Rubro", row['rubro'])
                        
                        u_sug = f1.number_input("Sugerido", value=float(row['monto_sugerido']))
                        u_conf = f2.number_input("Confirmado", value=float(row['monto_confirmado']))
                        u_fam = f3.text_input("Familia", row['grupo_familiar'])
                        
                        u_res = f1.text_input("Residencia", row['residencia'])
                        u_pas = f2.text_input("Próximo Paso", row['proximos_pasos'])
                        u_ctx = st.text_area("Contexto", row['contexto'])
                        
                        if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                            # Actualizar el DataFrame local
                            df.loc[idx] = [row['id'], u_nom, u_ape, u_tel, u_rub, u_ctx, u_res, u_fam, u_sug, u_est, u_conf, u_pas, u_resp, row['fecha_registro']]
                            if save_to_cloud(df):
                                st.success("¡Sincronizado!")
                                st.rerun()
                    
                    if st.button("🗑️ ELIMINAR", key=f"del_{row['id']}"):
                        df = df.drop(idx)
                        if save_to_cloud(df):
                            st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Nuevo Registro":
    st.subheader("Registrar Nuevo Donante")
    with st.form("n_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        r = c1.selectbox("Asignar Responsable", LISTA_RESPONSABLES)
        s = c2.number_input("Monto Sugerido (USD)", value=0.0)
        ctx = st.text_area("Notas de contexto")
        
        if st.form_submit_button("🚀 Crear y Guardar en la Nube"):
            if n:
                # Generamos ID único basado en tiempo
                new_id = str(int(datetime.now().timestamp()))
                # Creamos el registro nuevo
                new_row = pd.DataFrame([{
                    "id": new_id, "nombre": n, "apellido": a, "responsable": r, 
                    "monto_sugerido": s, "estado": "1. Por contactar", "monto_confirmado": 0, 
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                    "telefono": "-", "rubro": "-", "contexto": ctx, "residencia": "-", 
                    "grupo_familiar": "-", "proximos_pasos": "-"
                }])
                # Concatenamos y guardamos
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_to_cloud(updated_df):
                    st.success(f"¡{n} ha sido guardado exitosamente!")
                    # No usamos rerun aquí para que el mensaje de éxito sea visible un segundo
                    # pero forzamos el refresco de los datos para la próxima pestaña
            else:
                st.error("El nombre es obligatorio.")
