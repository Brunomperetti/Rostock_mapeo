import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Configuración de la página
st.set_page_config(layout="wide", page_title="Mapa Comercial Argentina")

# Título
st.title("🌍 Mapa Comercial de Argentina")

# Función para cargar y estandarizar datos
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        # Estandariza los nombres de columnas (ajusta según tus datos)
        column_mapping = {
            'lat': 'latitud',
            'lon': 'longitud',
            'Nombre': 'nombre',
            'Tipo': 'tipo',
            'Provincia': 'provincia'
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        return df[['latitud', 'longitud', 'nombre', 'tipo', 'provincia']].dropna()
    except Exception as e:
        st.error(f"Error al cargar archivo: {str(e)}")
        return None

# Sidebar para carga de archivos
with st.sidebar:
    st.header("📤 Carga de Datos")
    uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])
    
    st.header("⚙️ Filtros")
    if uploaded_file:
        df = load_data(uploaded_file)
        tipos = st.multiselect(
            "Tipos a mostrar:",
            options=df['tipo'].unique(),
            default=df['tipo'].unique()
        )
        provincias = st.multiselect(
            "Provincias:",
            options=df['provincia'].unique(),
            default=df['provincia'].unique()
        )
    else:
        st.warning("Por favor sube un archivo Excel")
        st.stop()

# Filtrar datos
if uploaded_file and df is not None:
    df_filtrado = df[
        (df['tipo'].isin(tipos)) & 
        (df['provincia'].isin(provincias))
    ]

    # Crear mapa
    fig = px.scatter_mapbox(
        df_filtrado,
        lat="latitud",
        lon="longitud",
        color="tipo",
        hover_name="nombre",
        hover_data=["provincia"],
        zoom=4,
        height=700,
        color_discrete_sequence=px.colors.qualitative.Plotly
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":0,"l":0,"b":0},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Mostrar datos
    with st.expander("📊 Ver datos tabulares"):
        st.dataframe(df_filtrado)

    # Botón para descargar
    st.download_button(
        label="📥 Descargar datos filtrados",
        data=df_filtrado.to_csv(index=False).encode('utf-8'),
        file_name="datos_filtrados.csv",
        mime="text/csv"
    )
else:
    st.warning("No se encontraron datos válidos para mostrar")
