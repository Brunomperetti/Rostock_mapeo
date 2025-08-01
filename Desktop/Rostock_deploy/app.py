import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de la página
st.set_page_config(layout="wide", page_title="Mapa Comercial Argentina")

# Título y descripción
st.title("🌍 Mapa Comercial de Argentina")
st.write("Visualización optimizada de clientes y oportunidades")

# Carga de datos (simplificada)
@st.cache_data
def load_data():
    # Aquí iría tu lógica de carga de archivos
    # Datos de ejemplo (reemplazar con tus datos reales)
    return pd.DataFrame({
        'latitud': [-34.6037, -31.4167, -32.8908, -24.7859, -27.7951],
        'longitud': [-58.3816, -64.1836, -68.8272, -65.4116, -64.2615],
        'tipo': ['Cliente Activo', 'Prospecto', 'Cliente Activo', 'Prospecto', 'Lista Pesada'],
        'nombre': ['Cliente A', 'Prospecto B', 'Cliente C', 'Prospecto D', 'Lista E']
    })

df = load_data()

# Mapa base de Argentina con Plotly Express
fig = px.scatter_mapbox(df,
                        lat="latitud",
                        lon="longitud",
                        color="tipo",
                        hover_name="nombre",
                        zoom=4,
                        height=600,
                        color_discrete_map={
                            'Cliente Activo': 'red',
                            'Prospecto': 'green',
                            'Lista Pesada': 'orange'
                        })

# Estilo del mapa (usa un estilo gratuito de Mapbox)
fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Mostrar el mapa
st.plotly_chart(fig, use_container_width=True)

# Panel de control en sidebar
with st.sidebar:
    st.header("⚙️ Configuración del Mapa")
    tipos = st.multiselect(
        "Filtrar por tipo:",
        options=df['tipo'].unique(),
        default=df['tipo'].unique()
    )
    tamaño_puntos = st.slider("Tamaño de los puntos", 5, 20, 10)
    
    # Actualizar filtros
    if tipos:
        df_filtrado = df[df['tipo'].isin(tipos)]
        fig.update_traces(marker=dict(size=tamaño_puntos),
                         selector=dict(mode='markers'))
        st.experimental_rerun()

