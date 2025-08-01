import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
from sklearn.cluster import DBSCAN
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from io import BytesIO
import openpyxl
import folium
from folium.plugins import MarkerCluster

# Configuración de la página
st.set_page_config(layout="wide", page_title="Oportunidades Comerciales en Argentina")

# Título
st.title("Análisis de Oportunidades Comerciales en Argentina")

# Sidebar para carga de datos
st.sidebar.header("Carga de Datos")
uploaded_files = {
    "base_fria": st.sidebar.file_uploader("Base Fría Geocodificada", type=["xlsx"]),
    "clientes_campana": st.sidebar.file_uploader("Clientes Campaña", type=["xlsx"]),
    "lista_pesada": st.sidebar.file_uploader("Lista Pesada", type=["xlsx"]),
    "rep_motor": st.sidebar.file_uploader("Repuestos Motor", type=["xlsx"]),
    "clientes_activos": st.sidebar.file_uploader("Clientes Activos", type=["xlsx"])
}

# Función para cargar y estandarizar datos
def load_and_standardize_data(uploaded_file, file_type):
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Estandarización según el tipo de archivo
            if file_type == "base_fria":
                df = df.rename(columns={
                    'Nombre': 'nombre',
                    'Provincia': 'provincia',
                    'Localidad': 'localidad',
                    'Dirección': 'direccion',
                    'Teléfono': 'telefono',
                    'lat': 'latitud',
                    'lon': 'longitud'
                })
                df['tipo'] = 'base_fria'
                df['potencial'] = 'bajo'
                
            elif file_type == "clientes_campana":
                df = df.rename(columns={
                    'Nombre': 'nombre',
                    'Provincia': 'provincia',
                    'Localidad': 'localidad',
                    'Teléfono': 'telefono',
                    'lat': 'latitud',
                    'lon': 'longitud'
                })
                df['tipo'] = 'cliente_campana'
                df['potencial'] = 'alto'
                df['direccion'] = None
                
            elif file_type == "lista_pesada":
                df = df.rename(columns={
                    'Nombre': 'nombre',
                    'Provincia': 'provincia',
                    'Teléfono': 'telefono',
                    'lat': 'latitud',
                    'lon': 'longitud'
                })
                df['tipo'] = 'lista_pesada'
                df['potencial'] = 'alto'
                df['localidad'] = None
                df['direccion'] = None
                
            elif file_type == "rep_motor":
                df = df.rename(columns={
                    'Nombre': 'nombre',
                    'Localidad': 'localidad',
                    'Provincia': 'provincia',
                    'Dirección': 'direccion',
                    'Teléfono': 'telefono',
                    'lat': 'latitud',
                    'lon': 'longitud'
                })
                df['tipo'] = 'rep_motor'
                df['potencial'] = 'bajo'
                
            elif file_type == "clientes_activos":
                df = df.rename(columns={
                    'Nombre': 'nombre',
                    'Domicilio': 'direccion',
                    'Localidad': 'localidad',
                    'Provincia': 'provincia',
                    'lat': 'latitud',
                    'lon': 'longitud'
                })
                df['tipo'] = 'cliente_activo'
                df['potencial'] = 'activo'
                df['telefono'] = None
                
            return df[['nombre', 'provincia', 'localidad', 'direccion', 'telefono', 'latitud', 'longitud', 'tipo', 'potencial']]
            
        except Exception as e:
            st.error(f"Error al cargar {file_type}: {str(e)}")
            return None
    return None

# Cargar todos los datos
dfs = []
for file_type, uploaded_file in uploaded_files.items():
    df = load_and_standardize_data(uploaded_file, file_type)
    if df is not None:
        dfs.append(df)

if not dfs:
    st.warning("Por favor, carga al menos un archivo de datos para comenzar el análisis.")
    st.stop()

# Combinar todos los DataFrames
full_df = pd.concat(dfs, ignore_index=True)

# Limpieza de datos
full_df = full_df.dropna(subset=['latitud', 'longitud'])
full_df['provincia'] = full_df['provincia'].str.upper().str.strip()

# Mostrar resumen de datos
st.header("Resumen de Datos Cargados")
col1, col2, col3 = st.columns(3)
col1.metric("Total de Registros", len(full_df))
col2.metric("Clientes Activos", len(full_df[full_df['potencial'] == 'activo']))
col3.metric("Leads Potenciales", len(full_df[full_df['potencial'] == 'alto']))

st.subheader("Distribución por Tipo")
st.bar_chart(full_df['tipo'].value_counts())

# Visualización en mapa (Folium)
st.header("Visualización Geográfica")

# Configuración del mapa
provincia_seleccionada = st.selectbox("Filtrar por Provincia:", ['TODAS'] + sorted(full_df['provincia'].unique().tolist()))

if provincia_seleccionada != 'TODAS':
    map_df = full_df[full_df['provincia'] == provincia_seleccionada]
else:
    map_df = full_df.copy()

# Crear el mapa base de Folium
m = folium.Map(location=[map_df['latitud'].mean(), map_df['longitud'].mean()], zoom_start=5)

# Añadir MarkerCluster
marker_cluster = MarkerCluster().add_to(m)

# Asignar colores según el tipo de potencial (alto, bajo, activo)
def get_color(potencial):
    if potencial == 'alto':
        return 'red'
    elif potencial == 'bajo':
        return 'orange'
    else:
        return 'green'

# Añadir los puntos de datos al mapa
for _, row in map_df.iterrows():
    folium.Marker(
        location=[row['latitud'], row['longitud']],
        popup=f"Nombre: {row['nombre']}<br>Provincia: {row['provincia']}<br>Localidad: {row['localidad']}<br>Tipo: {row['tipo']}",
        icon=folium.Icon(color=get_color(row['potencial']))
    ).add_to(marker_cluster)

# Mostrar el mapa interactivo
st.write(m)

# Análisis de oportunidades
st.header("Análisis de Oportunidades")

# Identificar clusters de alto potencial
if st.button("Identificar Zonas de Oportunidad"):
    alto_potencial = full_df[full_df['potencial'] == 'alto']
    
    if len(alto_potencial) > 0:
        # Convertir a coordenadas para clustering
        coords = alto_potencial[['latitud', 'longitud']].values
        
        # DBSCAN para identificar clusters geográficos
        kms_per_radian = 6371.0088
        epsilon = 50 / kms_per_radian  # 50km de radio
        
        db = DBSCAN(eps=epsilon, min_samples=3, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
        
        alto_potencial['cluster'] = db.labels_
        
        # Filtrar solo puntos que están en clusters (no ruido)
        clusters = alto_potencial[alto_potencial['cluster'] >= 0]
        
        if len(clusters) > 0:
            # Calcular centroides de los clusters
            centroides = clusters.groupby('cluster')[['latitud', 'longitud']].mean().reset_index()
            
            # Contar clientes activos cerca de cada centroide
            def count_nearby_active(centroide, radius_km=50):
                activos = full_df[full_df['potencial'] == 'activo']
                if len(activos) == 0:
                    return 0
                
                distances = activos.apply(
                    lambda row: geodesic((row['latitud'], row['longitud']), (centroide['latitud'], centroide['longitud'])).km,
                    axis=1
                )
                return len(distances[distances <= radius_km])
            
            centroides['activos_cercanos'] = centroides.apply(count_nearby_active, axis=1)
            
            # Ordenar por menor presencia de clientes activos (mayor oportunidad)
            oportunidades = centroides.sort_values('activos_cercanos').head(5)
            
            st.subheader("Top 5 Zonas de Oportunidad")
            st.write("Estas zonas tienen alta concentración de leads potenciales y baja presencia de clientes activos: ")
            
            # Mostrar tabla con oportunidades
            st.dataframe(oportunidades)
            
            # Mapa de oportunidades
            st.subheader("Mapa de Oportunidades")
            
            # Capa de clusters
            cluster_layer = pdk.Layer(
                "ScatterplotLayer",
                clusters,
                pickable=True,
                opacity=0.8,
                stroked=True,
                filled=True,
                radius_scale=10,
                radius_min_pixels=5,
                radius_max_pixels=15,
                line_width_min_pixels=1,
                get_position=['longitud', 'latitud'],
                get_color=[255, 0, 0, 160],
                get_radius=200,
            )
            
            # Capa de centroides
            centroide_layer = pdk.Layer(
                "ScatterplotLayer",
                oportunidades,
                pickable=True,
                opacity=0.8,
                stroked=True,
                filled=True,
                radius_scale=20,
                radius_min_pixels=10,
                radius_max_pixels=30,
                line_width_min_pixels=2,
                get_position=['longitud', 'latitud'],
                get_color=[0, 0, 255, 200],
                get_radius=500,
            )
            
            # Vista del mapa
            view_state = pdk.ViewState(
                latitude=oportunidades['latitud'].mean(),
                longitude=oportunidades['longitud'].mean(),
                zoom=5,
                pitch=0
            )
            
            # Tooltip para centroides
            tooltip = {
                "html": "<b>Zona de Oportunidad</b><br/>"
                        "<b>Clientes activos cercanos:</b> {activos_cercanos}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white"
                }
            }
            
            # Renderizar mapa
            st.pydeck_chart(pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=view_state,
                layers=[cluster_layer, centroide_layer],
                tooltip=tooltip
            ))
            
        else:
            st.warning("No se encontraron clusters significativos de leads potenciales.")
    else:
        st.warning("No hay datos de leads potenciales para analizar.")

# Recomendaciones basadas en el análisis
st.header("Recomendaciones de Expansión")

if st.button("Generar Recomendaciones"):
    # Aquí iría la lógica más sofisticada para generar recomendaciones
    # Por ahora un ejemplo simple basado en provincias con más leads potenciales
    
    provincias_potencial = full_df[full_df['potencial'] == 'alto']['provincia'].value_counts().head(5)
    provincias_activos = full_df[full_df['potencial'] == 'activo']['provincia'].value_counts()
    
    # Priorizar provincias con muchos leads pero pocos clientes activos
    oportunidades = []
    for provincia, count in provincias_potencial.items():
        activos = provincias_activos.get(provincia, 0)
        ratio = count / (activos + 1)  # Evitar división por cero
        oportunidades.append({'Provincia': provincia, 'Leads Potenciales': count, 'Clientes Activos': activos, 'Ratio': ratio})
    
    oportunidades_df = pd.DataFrame(oportunidades).sort_values('Ratio', ascending=False)
    
    st.subheader("Top Provincias con Mayor Oportunidad")
    st.write("Estas provincias tienen alta concentración de leads potenciales en relación a clientes activos:")
    st.dataframe(oportunidades_df)
    
    # Gráfico de barras
    fig, ax = plt.subplots()
    oportunidades_df.set_index('Provincia')['Ratio'].plot(kind='bar', ax=ax, color='green')
    ax.set_title("Ratio Leads Potenciales / Clientes Activos por Provincia")
    ax.set_ylabel("Ratio")
    st.pyplot(fig)

# Exportar resultados
st.sidebar.header("Exportar Resultados")
if st.sidebar.button("Exportar Datos Consolidados"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        full_df.to_excel(writer, index=False)
    st.sidebar.download_button(
        label="Descargar Excel",
        data=output.getvalue(),
        file_name="datos_consolidados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )





