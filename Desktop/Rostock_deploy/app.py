import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import requests
from io import BytesIO

# Configuración de la página
st.set_page_config(layout="wide", page_title="Oportunidades Comerciales en Argentina")

# Título
st.title("📊 Análisis de Oportunidades Comerciales en Argentina")

# Cargar imagen de fondo del mapa de Argentina (versión liviana)
@st.cache_data
def cargar_mapa_argentina():
    try:
        url = "https://raw.githubusercontent.com/deldersveld/topojson/master/countries/argentina/argentina-provinces.png"
        response = requests.get(url)
        return Image.open(BytesIO(response.content))
    except:
        # Crear fondo simple si falla la descarga
        img = Image.new('RGB', (800, 1000), (240, 240, 240))
        return img

mapa_arg = cargar_mapa_argentina()

# Sidebar para carga de datos
with st.sidebar:
    st.header("⚙️ Configuración")
    uploaded_files = {
        "base_fria": st.file_uploader("Base Fría Geocodificada", type=["xlsx"]),
        "clientes_campana": st.file_uploader("Clientes Campaña", type=["xlsx"]),
        "lista_pesada": st.file_uploader("Lista Pesada", type=["xlsx"]),
        "rep_motor": st.file_uploader("Repuestos Motor", type=["xlsx"]),
        "clientes_activos": st.file_uploader("Clientes Activos", type=["xlsx"])
    }
    
    # Opciones de visualización
    st.header("🎨 Opciones de Visualización")
    tamano_puntos = st.slider("Tamaño de los puntos", 10, 100, 50)
    opacidad = st.slider("Opacidad de los puntos", 0.1, 1.0, 0.7)

# Función para cargar y estandarizar datos (versión simplificada)
@st.cache_data
def cargar_datos(uploaded_files):
    dfs = []
    for file_type, uploaded_file in uploaded_files.items():
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                # Estandarización básica
                rename_cols = {
                    'Nombre': 'nombre', 'Provincia': 'provincia', 
                    'Localidad': 'localidad', 'Dirección': 'direccion',
                    'Teléfono': 'telefono', 'lat': 'latitud', 'lon': 'longitud'
                }
                df = df.rename(columns={k: v for k, v in rename_cols.items() if k in df.columns})
                df['tipo'] = file_type.replace("_", " ").title()
                dfs.append(df)
            except Exception as e:
                st.error(f"Error al cargar {file_type}: {str(e)}")
    return pd.concat(dfs, ignore_index=True) if dfs else None

# Cargar datos
full_df = cargar_datos(uploaded_files)

if full_df is None:
    st.warning("⏳ Por favor, carga al menos un archivo de datos para comenzar el análisis.")
    st.stop()

# Limpieza básica
full_df = full_df.dropna(subset=['latitud', 'longitud'])
full_df['provincia'] = full_df['provincia'].str.upper().str.strip()

# Mostrar resumen de datos
st.header("📌 Resumen de Datos")
cols = st.columns(4)
cols[0].metric("Total Registros", len(full_df))
cols[1].metric("Clientes Activos", len(full_df[full_df['tipo'] == 'Clientes Activos']))
cols[2].metric("Leads Potenciales", len(full_df[full_df['tipo'].isin(['Clientes Campana', 'Lista Pesada'])]))
cols[3].metric("Provincias", full_df['provincia'].nunique())

# Visualización Geográfica Alternativa
st.header("🗺️ Visualización Geográfica")

# Coordenadas aproximadas de Argentina para mapeo
ARG_LAT_RANGE = (-55, -20)
ARG_LON_RANGE = (-75, -50)

# Función para convertir coordenadas a posición en la imagen
def coords_to_pixels(lat, lon, img_width, img_height):
    x = img_width * (lon - ARG_LON_RANGE[0]) / (ARG_LON_RANGE[1] - ARG_LON_RANGE[0])
    y = img_height * (1 - (lat - ARG_LAT_RANGE[0]) / (ARG_LAT_RANGE[1] - ARG_LAT_RANGE[0]))
    return np.clip(x, 0, img_width), np.clip(y, 0, img_height)

# Configurar el gráfico
fig, ax = plt.subplots(figsize=(12, 15))
ax.imshow(mapa_arg, extent=[0, 100, 0, 100])

# Colores y marcadores por tipo
config_visual = {
    'Base Fria': {'color': '#1f77b4', 'marker': 'o'},
    'Clientes Campana': {'color': '#2ca02c', 'marker': 's'},
    'Lista Pesada': {'color': '#ff7f0e', 'marker': '^'},
    'Repuestos Motor': {'color': '#9467bd', 'marker': 'p'},
    'Clientes Activos': {'color': '#d62728', 'marker': 'D'}
}

# Filtrar por provincia si es necesario
provincia_seleccionada = st.selectbox("Filtrar por Provincia:", 
                                    ['TODAS'] + sorted(full_df['provincia'].unique().tolist()),
                                    index=0)

if provincia_seleccionada != 'TODAS':
    map_df = full_df[full_df['provincia'] == provincia_seleccionada]
else:
    map_df = full_df.copy()

# Dibujar puntos agrupados por tipo
for tipo, grupo in map_df.groupby('tipo'):
    if tipo in config_visual:
        x_coords, y_coords = [], []
        for _, row in grupo.iterrows():
            x, y = coords_to_pixels(row['latitud'], row['longitud'], 100, 100)
            x_coords.append(x)
            y_coords.append(y)
        
        ax.scatter(x_coords, y_coords, 
                  color=config_visual[tipo]['color'],
                  marker=config_visual[tipo]['marker'],
                  s=tamano_puntos,
                  alpha=opacidad,
                  label=tipo)

# Configuración del gráfico
ax.axis('off')
ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
plt.tight_layout()

# Mostrar el gráfico
st.pyplot(fig)

# Análisis por provincias
st.header("📈 Análisis por Provincia")
provincia_stats = full_df['provincia'].value_counts().reset_index()
provincia_stats.columns = ['Provincia', 'Cantidad']

col1, col2 = st.columns(2)
with col1:
    st.bar_chart(provincia_stats.set_index('Provincia'))

with col2:
    st.dataframe(provincia_stats, height=400)

# Opción para descargar datos
if st.button("💾 Descargar Datos Procesados"):
    csv = full_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar CSV",
        data=csv,
        file_name="datos_clientes_argentina.csv",
        mime="text/csv"
    )

