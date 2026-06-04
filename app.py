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
        # Lee la primera pestaña disponible (Sheet1 por defecto)
        data = conn.read(ttl=0)
        if data is None or data.empty:
            raise ValueError("Vacío")
        # Limpieza de datos numéricos
        data['monto_confirmado'] = pd.to_numeric(data['monto_confirmado'], errors='coerce').fillna(0)
        data['monto_sugerido'] = pd.to_numeric(data['monto_sugerido'], errors='coerce').fillna(0)
        return data
    except:
        # Estructura base si el Excel está recién creado
        return pd.DataFrame(columns=[
            "id", "nombre", "apellido", "telefono", "rubro", "contexto", 
            "residencia", "grupo_familiar", "monto_sugerido", "estado", 
            "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"
        ])

def save_data(dataframe):
    # Convertimos a string para asegurar persistencia en GSheets
    dataframe_to_save = dataframe.astype(str)
    conn.update(data=dataframe_to_save)
    st.cache_data.clear()

# --- CONSTANTES ---
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

# --- INICIALIZACIÓN ---
df = load_data()

# Si no hay columnas correctas, inicializamos con Seed Data
if "nombre" not in df.columns:
    st.info("Inicializando estructura de datos...")
    columnas = ["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"]
    seed = [{
        "id": "1", "nombre": "Jorge / Alex", "apellido": "Szuster", "telefono": "+54 9 11 5428-3546",
        "rubro": "Insumos Hospitalarios", "contexto": "Vende colchones.", "residencia": "Chateau", 
        "grupo_familiar": "-", "monto_sugerido": "50000", "estado": "1. Por contactar", 
        "monto_confirmado": "0", "proximos_pasos": "Llamar semana proxima", "responsable": "Julian Barki", 
        "fecha_registro": datetime.now().strftime("%Y-%m-%d")
    }]
    df = pd.DataFrame(seed, columns=columnas)
    save_data(df)
    st.rerun()

# --- LÓGICA DE RESPONSABLES DINÁMICOS ---
# El sistema lee quiénes ya son responsables en la base de datos
responsables_existentes = sorted(df['responsable'].unique().tolist())
if "Equipo General" not in responsables_existentes:
    responsables_existentes = ["Equipo General"] + responsables_existentes

# --- SIDEBAR ---
st.sidebar.title("🛡️ CRM Seguridad")
meta_usd = st.sidebar.number_input("Meta de Recaudación (USD)", value=500000, step=10000)
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo"])

# --- DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Estado de la Recaudación")
    
    recaudado = df['monto_confirmado'].sum()
    sugerido_negoc = df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'].sum()
    proyectado = recaudado + sugerido_negoc
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {recaudado:,.0f}")
    c2.metric("PROYECTADO (Pipeline)", f"USD {proyectado:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, meta_usd - recaudado):,.0f}")
    c4.metric("TOTAL CONTACTOS", len(df))

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    
    with col_a:
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=recaudado,
            delta={'reference': proyectado, 'position': "top", 'increasing': {'color': "blue"}},
            gauge={'axis': {'range': [None, meta_usd]}, 'bar': {'color': "#2ecc71"}},
            title={'text': "Progreso vs Meta"}))
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        st.subheader("USD por Responsable")
        resp_money = df.groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        st.plotly_chart(px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', color_discrete_sequence=['#3498db']), use_container_width=True)

# --- PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Pipeline Operativo")
    
    col_f1, col_f2 = st.columns([3, 1])
    search = col_f1.text_input("🔍 Buscar (Nombre, Rubro, Notas...)").lower()
    f_resp = col_f2.selectbox("Filtrar Encargado", ["Todos"] + responsables_existentes)
    
    df_f = df[df.apply(lambda r: search in str(r).lower(), axis=1)]
    if f_resp != "Todos":
        df_f = df_f[df_f['responsable'] == f_resp]

    for index, row in df_f.iterrows():
        emoji = "🔵" if "1." in str(row['estado']) else "🟢" if "6." in str(row['estado']) else "🔴" if "7." in str(row['estado']) else "🟡"
        
        with st.expander(f"{emoji} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            c_h1, c_h2 = st.columns([2, 1])
            with c_h1:
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            with c_h2:
                col_b1, col_b2, col_b3 = st.columns(3)
                if col_b1.button("✅", key=f"q_c_{index}", help="Confirmar"):
                    df.at[index, 'estado'] = '6. Donación Confirmada'
                    save_data(df); st.rerun()
                if col_b2.button("❌", key=f"q_r_{index}", help="Rechazo"):
                    df.at[index, 'estado'] = '7. Rechazó'
                    save_data(df); st.rerun()
                edit_mode = col_b3.toggle("✏️", key=f"tog_{index}")

            if not edit_mode:
                st.markdown("---")
                col_izq, col_der = st.columns(2)
                with col_izq:
                    st.write(f"**📞 Tel:** {row['telefono']}")
                    st.write(f"**💼 Rubro:** {row['rubro']}")
                    st.write(f"**👨‍👩‍👧 Familia:** {row['grupo_familiar']}")
                with col_der:
                    st.write(f"**📓 Contexto:** {row['contexto']}")
                    st.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_ed_{index}"):
                    f1, f2, f3 = st.columns(3)
                    u_nom = f1.text_input("Nombre", row['nombre'])
                    u_ape = f2.text_input("Apellido", row['apellido'])
                    u_tel = f3.text_input("Teléfono", row['telefono'])
                    
                    # Selección o nuevo responsable
                    u_resp_ex = f1.selectbox("Responsable Actual", responsables_existentes, index=responsables_existentes.index(row['responsable']) if row['responsable'] in responsables_existentes else 0)
                    u_resp_new = f2.text_input("Cambiar a Nuevo Responsable (opcional)")
                    u_rub = f3.text_input("Rubro", row['rubro'])
                    
                    u_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    u_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                    u_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                    
                    u_ctx = st.text_area("Contexto", row['contexto'])
                    u_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    u_fam = st.text_input("Familia", row['grupo_familiar'])
                    u_res = st.text_input("Residencia", row['residencia'])
                    
                    if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                        final_resp = u_resp_new if u_resp_new else u_resp_ex
                        df.loc[index] = [row['id'], u_nom, u_ape, u_tel, u_rub, u_ctx, u_res, u_fam, u_sug, u_est, u_conf, u_pas, final_resp, row['fecha_registro']]
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
        
        st.markdown("---")
        r_ex = c1.selectbox("Elegir Responsable Existente", responsables_existentes)
        r_new = c2.text_input("O escribir Nombre de Nuevo Responsable")
        st.markdown("---")
        
        rub = c1.text_input("Rubro")
        sug = c2.number_input("Monto Sugerido", value=0.0)
        ctx = st.text_area("Notas de contexto")
        
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                final_r = r_new if r_new else r_ex
                new_data = pd.DataFrame([{
                    "id": str(len(df) + 1), "nombre": n, "apellido": a, "telefono": "-", "rubro": rub, "contexto": ctx, "residencia": "-", "grupo_familiar": "-", 
                    "monto_sugerido": str(sug), "estado": "1. Por contactar", "monto_confirmado": "0", "proximos_pasos": "-", "responsable": final_r, "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df); st.success(f"¡Registrado con {final_r}!"); st.rerun()
