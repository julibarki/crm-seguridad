import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Security CRM Enterprise Gold", layout="wide", page_icon="🛡️")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet="Sheet1"):
    try:
        return conn.read(worksheet=worksheet, ttl=0)
    except:
        return pd.DataFrame()

def save_data(dataframe, worksheet="Sheet1"):
    dataframe = dataframe.astype(str)
    conn.update(worksheet=worksheet, data=dataframe)
    st.cache_data.clear()

# --- INICIALIZACIÓN DE DATOS Y CONFIGURACIÓN ---
df = load_data(worksheet="Sheet1")
df_conf = load_data(worksheet="Configuracion")

# 1. Verificar/Inicializar Responsables y Meta
if df_conf.empty:
    df_conf = pd.DataFrame([
        {"clave": "meta_recaudacion", "valor": "500000"},
        {"clave": "responsable", "valor": "Equipo General"},
        {"clave": "responsable", "valor": "Julian Barki"},
        {"clave": "responsable", "valor": "Ariel Goldman"}
    ])
    save_data(df_conf, worksheet="Configuracion")

# 2. Extraer Configuración
meta_actual = float(df_conf[df_conf['clave'] == 'meta_recaudacion']['valor'].iloc[0])
lista_responsables = df_conf[df_conf['clave'] == 'responsable']['valor'].tolist()

# 3. Inicializar Donantes si está vacío
ESTADOS = ["1. Por contactar", "2. Primer mensaje enviado", "3. Reunión pactada", "4. Reunión realizada", "5. Aceptó donar (Falta definir monto)", "6. Donación Confirmada", "7. Rechazó"]

if df.empty or "nombre" not in df.columns:
    columnas = ["id", "nombre", "apellido", "telefono", "rubro", "contexto", "residencia", "grupo_familiar", "monto_sugerido", "estado", "monto_confirmado", "proximos_pasos", "responsable", "fecha_registro"]
    seed = [{
        "id": "1", "nombre": "Jorge / Alex", "apellido": "Szuster", "telefono": "+54 9 11 5428-3546",
        "rubro": "Insumos Hospitalarios", "contexto": "Vende colchones, mucha plata.", "residencia": "Chateau/Hacoaj", 
        "grupo_familiar": "-", "monto_sugerido": "50000", "estado": "1. Por contactar", 
        "monto_confirmado": "0", "proximos_pasos": "Llamar semana proxima", "responsable": "Equipo General", 
        "fecha_registro": datetime.now().strftime("%Y-%m-%d")
    }]
    df = pd.DataFrame(seed, columns=columnas)
    save_data(df, worksheet="Sheet1")
    st.rerun()

# --- INTERFAZ ---
st.sidebar.title("🛡️ Security CRM Pro")
menu = st.sidebar.radio("Navegación", ["📊 Dashboard Ejecutivo", "👥 Pipeline de Gestión", "🆕 Registrar Nuevo", "⚙️ Configuración"])

# --- VISTA: DASHBOARD ---
if menu == "📊 Dashboard Ejecutivo":
    st.title("Centro de Mando Estratégico")
    
    confirmado = pd.to_numeric(df['monto_confirmado'], errors='coerce').fillna(0).sum()
    sugerido_negoc = pd.to_numeric(df[df['estado'].isin(ESTADOS[1:5])]['monto_sugerido'], errors='coerce').fillna(0).sum()
    proyectado = confirmado + sugerido_negoc
    
    total_contactos = len(df)
    contactados = len(df[df['estado'] != "1. Por contactar"])
    tasa_llamadas = (contactados/total_contactos*100) if total_contactos > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RECAUDADO REAL", f"USD {confirmado:,.0f}")
    c2.metric("PROYECTADO (Pipeline)", f"USD {proyectado:,.0f}")
    c3.metric("FALTANTE META", f"USD {max(0, meta_actual - confirmado):,.0f}")
    c4.metric("GESTIÓN", f"{tasa_llamadas:.1f}% llamado")

    st.markdown("---")
    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=confirmado,
            delta={'reference': proyectado, 'position': "top", 'increasing': {'color': "blue"}},
            gauge={'axis': {'range': [None, meta_actual]}, 'bar': {'color': "#2ecc71"}},
            title={'text': "Progreso vs Meta"}))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        resp_money = df.groupby('responsable')['monto_confirmado'].sum().sort_values().reset_index()
        st.plotly_chart(px.bar(resp_money, x='monto_confirmado', y='responsable', orientation='h', title="Ranking Recaudación"), use_container_width=True)

# --- VISTA: PIPELINE ---
elif menu == "👥 Pipeline de Gestión":
    st.title("Pipeline Operativo")
    
    col_f1, col_f2 = st.columns([3, 1])
    search = col_f1.text_input("🔍 Buscar (Nombre, Rubro, Contexto, Familia...)")
    f_resp = col_f2.selectbox("Filtrar por Responsable", ["Todos"] + lista_responsables)
    
    df_f = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    if f_resp != "Todos": df_f = df_f[df_f['responsable'] == f_resp]

    for index, row in df_f.iterrows():
        color = "🔵" if "1." in str(row['estado']) else "🟢" if "6." in str(row['estado']) else "🟡"
        with st.expander(f"{color} {row['nombre']} {row['apellido']} | {row['estado']} | {row['responsable']}"):
            
            c_header_1, c_header_2 = st.columns([2, 1])
            with c_header_1:
                st.markdown(f"💰 **Sugerido:** USD {float(row['monto_sugerido']):,.0f} | **Confirmado:** :green[USD {float(row['monto_confirmado']):,.0f}]")
            with c_header_2:
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
                    st.write(f"📞 **Tel:** {row['telefono']}")
                    st.write(f"💼 **Rubro:** {row['rubro']}")
                    st.write(f"🏠 **Residencia:** {row['residencia']}")
                    st.write(f"👨‍👩‍👧 **Familia:** {row['grupo_familiar']}")
                with col_der:
                    st.write(f"📓 **Contexto:** {row['contexto']}")
                    st.markdown(f"🚀 **Próximo Paso:** :orange[{row['proximos_pasos']}]")
            else:
                with st.form(key=f"form_ed_{index}"):
                    f1, f2, f3 = st.columns(3)
                    un_nom = f1.text_input("Nombre", row['nombre'])
                    un_ape = f2.text_input("Apellido", row['apellido'])
                    un_resp = f3.selectbox("Responsable", lista_responsables, index=lista_responsables.index(row['responsable']) if row['responsable'] in lista_responsables else 0)
                    
                    un_est = f1.selectbox("Estado", ESTADOS, index=ESTADOS.index(row['estado']) if row['estado'] in ESTADOS else 0)
                    un_sug = f2.number_input("Sugerido", value=float(row['monto_sugerido']))
                    un_conf = f3.number_input("Confirmado", value=float(row['monto_confirmado']))
                    
                    un_tel = f1.text_input("Teléfono", row['telefono'])
                    un_res = f2.text_input("Residencia", row['residencia'])
                    un_fam = f3.text_input("Familia", row['grupo_familiar'])
                    un_pas = st.text_input("Próximo Paso", row['proximos_pasos'])
                    un_ctx = st.text_area("Contexto", row['contexto'])
                    
                    if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                        df.loc[index] = [row['id'], un_nom, un_ape, un_tel, un_rub, un_ctx, un_res, un_fam, un_sug, un_est, un_conf, un_pas, un_resp, row['fecha_registro']]
                        save_data(df); st.rerun()
                
                if st.button("🗑️ ELIMINAR DONANTE", key=f"del_{index}"):
                    df = df.drop(index); save_data(df); st.rerun()

# --- VISTA: NUEVO ---
elif menu == "🆕 Registrar Nuevo":
    st.subheader("Registrar Nuevo Donante")
    with st.form("nuevo_prospecto"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre *")
        a = c2.text_input("Apellido")
        resp = c1.selectbox("Responsable", lista_responsables)
        rub = c2.text_input("Rubro")
        sug = c1.number_input("Monto Sugerido", value=0.0)
        ctx = st.text_area("Notas de contexto")
        if st.form_submit_button("🚀 Crear Donante"):
            if n:
                new_data = pd.DataFrame([{
                    "id": str(len(df) + 1), "nombre": n, "apellido": a, "telefono": "-", "rubro": rub, "contexto": ctx, "residencia": "-", "grupo_familiar": "-", 
                    "monto_sugerido": str(sug), "estado": "1. Por contactar", "monto_confirmado": "0", "proximos_pasos": "-", "responsable": resp, "fecha_registro": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df); st.success("¡Registrado!"); st.rerun()

# --- VISTA: CONFIGURACIÓN ---
elif menu == "⚙️ Configuración":
    st.title("Configuración del Sistema")
    
    # 1. Meta Recaudación
    st.subheader("🎯 Meta del Proyecto")
    n_meta = st.number_input("Meta Global USD", value=meta_actual, step=10000.0)
    if st.button("Actualizar Meta"):
        df_conf.loc[df_conf['clave'] == 'meta_recaudacion', 'valor'] = str(n_meta)
        save_data(df_conf, worksheet="Configuracion"); st.success("Meta actualizada"); st.rerun()

    st.markdown("---")
    
    # 2. Gestión de Responsables
    st.subheader("👥 Gestión de Responsables")
    with st.form("add_resp", clear_on_submit=True):
        nuevo_r = st.text_input("Nombre del nuevo responsable")
        if st.form_submit_button("Añadir"):
            if nuevo_r and nuevo_r not in lista_responsables:
                new_resp_row = pd.DataFrame([{"clave": "responsable", "valor": nuevo_r}])
                df_conf = pd.concat([df_conf, new_resp_row], ignore_index=True)
                save_data(df_conf, worksheet="Configuracion"); st.rerun()

    st.write("**Lista Actual:**")
    for r in lista_responsables:
        colr1, colr2 = st.columns([3, 1])
        colr1.write(f"• {r}")
        if r != "Equipo General" and colr2.button("Borrar", key=f"br_{r}"):
            df_conf = df_conf[df_conf['valor'] != r]
            save_data(df_conf, worksheet="Configuracion"); st.rerun()
