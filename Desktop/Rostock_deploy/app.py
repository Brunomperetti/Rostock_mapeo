import streamlit as st
import pandas as pd
import folium
from io import BytesIO
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

# Visualización en mapa con Folium
st.header("Visualización Geográfica")

# Configuración del mapa
provincia_seleccionada = st.selectbox("Filtrar por Provincia:", ['TODAS'] + sorted(full_df['provincia'].unique().tolist()))

if provincia_seleccionada != 'TODAS':
    map_df = full_df[full_df['provincia'] == provincia_seleccionada]
else:
    map_df = full_df.copy()

# Crear mapa de Folium
m = folium.Map(location=[map_df['latitud'].mean(), map_df['longitud'].mean()], zoom_start=5)

# Agregar MarkerCluster
marker_cluster = MarkerCluster().add_to(m)

# Añadir marcadores al mapa
for _, row in map_df.iterrows():
    folium.Marker(
        location=[row['latitud'], row['longitud']],
        popup=f"Nombre: {row['nombre']}<br>Provincia: {row['provincia']}<br>Localidad: {row['localidad']}<br>Tipo: {row['tipo']}",
        icon=folium.Icon(color='red' if row['potencial'] == 'alto' else 'blue')
    ).add_to(marker_cluster)

# Mostrar mapa en Streamlit
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
            st.write("Estas zonas tienen alta concentración de leads potenciales y baja presencia de clientes activos:")
            
            # Mostrar tabla con oportunidades
            st.dataframe(oportunidades)
            
        else:
            st.warning("No se encontraron clusters significativos de leads potenciales.")
    else:
        st.warning("No hay datos de leads potenciales para analizar.")


