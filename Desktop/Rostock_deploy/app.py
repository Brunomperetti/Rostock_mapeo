import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from sklearn.cluster import DBSCAN
import numpy as np
from geopy.distance import geodesic
from io import BytesIO

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

# Función para cargar y estandarizar datos (con caché)
@st.cache_data
def load_and_standardize_data(uploaded_file, file_type):
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Estandarización según el tipo de archivo
            if file_type == "base_fria":
                df = df.rename(columns={
                    'Nombre': 'nombre', 'Provincia': 'provincia', 
                    'Localidad': 'localidad', 'Dirección': 'direccion',
                    'Teléfono': 'telefono', 'lat': 'latitud', 'lon': 'longitud'
                })
                df['tipo'] = 'Base Fría'
                df['potencial'] = 'bajo'

            elif file_type == "clientes_campana":
                df = df.rename(columns={
                    'Nombre': 'nombre', 'Provincia': 'provincia',
                    'Localidad': 'localidad', 'Teléfono': 'telefono',
                    'lat': 'latitud', 'lon': 'longitud'
                })
                df['tipo'] = 'Clientes Campaña'
                df['potencial'] = 'alto'
                df['direccion'] = None

            elif file_type == "lista_pesada":
                df = df.rename(columns={
                    'Nombre': 'nombre', 'Provincia': 'provincia',
                    'Teléfono': 'telefono', 'lat': 'latitud', 'lon': 'longitud'
                })
                df['tipo'] = 'Lista Pesada'
                df['potencial'] = 'alto'
                df['localidad'] = None
                df['direccion'] = None

            elif file_type == "rep_motor":
                df = df.rename(columns={
                    'Nombre': 'nombre', 'Localidad': 'localidad',
                    'Provincia': 'provincia', 'Dirección': 'direccion',
                    'Teléfono': 'telefono', 'lat': 'latitud', 'lon': 'longitud'
                })
                df['tipo'] = 'Repuestos Motor'
                df['potencial'] = 'bajo'

            elif file_type == "clientes_activos":
                df = df.rename(columns={
                    'Nombre': 'nombre', 'Domicilio': 'direccion',
                    'Localidad': 'localidad', 'Provincia': 'provincia',
                    'lat': 'latitud', 'lon': 'longitud'
                })
                df['tipo'] = 'Clientes Activos'
                df['potencial'] = 'activo'
                df['telefono'] = None

            # Asegurar que las coordenadas sean numéricas
            df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
            df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
            
            return df[['nombre', 'provincia', 'localidad', 'direccion', 'telefono', 
                      'latitud', 'longitud', 'tipo', 'potencial']].dropna(subset=['latitud', 'longitud'])

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
provincia_seleccionada = st.selectbox("Filtrar por Provincia:", 
                                    ['TODAS'] + sorted(full_df['provincia'].unique().tolist()))

if provincia_seleccionada != 'TODAS':
    map_df = full_df[full_df['provincia'] == provincia_seleccionada]
else:
    map_df = full_df.copy()

# Crear mapa de Folium con ubicación centrada
map_center = [map_df['latitud'].mean(), map_df['longitud'].mean()]
m = folium.Map(location=map_center, zoom_start=5 if provincia_seleccionada == 'TODAS' else 8)

# Agregar MarkerCluster
marker_cluster = MarkerCluster().add_to(m)

# Configuración de iconos por tipo
icon_config = {
    'Base Fría': {'color': 'blue', 'icon': 'info-sign'},
    'Clientes Campaña': {'color': 'green', 'icon': 'user'},
    'Lista Pesada': {'color': 'orange', 'icon': 'shopping-cart'},
    'Repuestos Motor': {'color': 'purple', 'icon': 'wrench'},
    'Clientes Activos': {'color': 'red', 'icon': 'star'}
}

# Añadir marcadores al mapa con popups mejorados
for _, row in map_df.iterrows():
    icon_settings = icon_config.get(row['tipo'], {'color': 'gray', 'icon': 'question-sign'})
    
    popup_content = f"""
    <div style="width: 250px;">
        <h4 style="margin:0;color:{icon_settings['color']}">{row['tipo']}</h4>
        <p><b>Nombre:</b> {row['nombre']}</p>
        <p><b>Provincia:</b> {row['provincia']}</p>
        {f"<p><b>Localidad:</b> {row['localidad']}</p>" if pd.notna(row['localidad']) else ""}
        {f"<p><b>Dirección:</b> {row['direccion']}</p>" if pd.notna(row['direccion']) else ""}
        {f"<p><b>Teléfono:</b> {row['telefono']}</p>" if pd.notna(row['telefono']) else ""}
        <p><b>Potencial:</b> {row['potencial'].capitalize()}</p>
    </div>
    """
    
    folium.Marker(
        location=[row['latitud'], row['longitud']],
        popup=folium.Popup(popup_content, max_width=300),
        icon=folium.Icon(
            color=icon_settings['color'],
            icon=icon_settings['icon'],
            prefix='glyphicon'
        )
    ).add_to(marker_cluster)

# Añadir leyenda
legend_html = """
<div style="position: fixed; 
     bottom: 50px; left: 50px; width: 180px; height: 160px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white;
     padding: 10px;
     border-radius: 5px;">
     <b>Leyenda</b><br>
     &nbsp; <i class="glyphicon glyphicon-star" style="color:red"></i> Clientes Activos<br>
     &nbsp; <i class="glyphicon glyphicon-user" style="color:green"></i> Clientes Campaña<br>
     &nbsp; <i class="glyphicon glyphicon-shopping-cart" style="color:orange"></i> Lista Pesada<br>
     &nbsp; <i class="glyphicon glyphicon-info-sign" style="color:blue"></i> Base Fría<br>
     &nbsp; <i class="glyphicon glyphicon-wrench" style="color:purple"></i> Repuestos Motor
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# Mostrar mapa en Streamlit
st.components.v1.html(m._repr_html_(), height=600)

# Análisis de oportunidades
st.header("Análisis de Oportunidades")

if st.button("Identificar Zonas de Oportunidad"):
    alto_potencial = full_df[full_df['potencial'] == 'alto']
    
    if len(alto_potencial) > 0:
        coords = alto_potencial[['latitud', 'longitud']].values
        
        # DBSCAN para identificar clusters geográficos
        kms_per_radian = 6371.0088
        epsilon = 50 / kms_per_radian  # 50km de radio
        
        with st.spinner('Analizando clusters...'):
            db = DBSCAN(eps=epsilon, min_samples=3, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
            alto_potencial['cluster'] = db.labels_
            
            # Filtrar solo puntos que están en clusters (no ruido)
            clusters = alto_potencial[alto_potencial['cluster'] >= 0]
            
            if len(clusters) > 0:
                # Calcular centroides
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
                
                # Ordenar por menor presencia de clientes activos
                oportunidades = centroides.sort_values('activos_cercanos').head(5)
                
                st.subheader("Top 5 Zonas de Oportunidad")
                st.write("Zonas con alta concentración de leads potenciales y baja presencia de clientes activos:")
                
                # Mostrar resultados
                st.dataframe(oportunidades)
                
                # Mostrar en mapa
                m_oportunidades = folium.Map(location=map_center, zoom_start=5)
                
                # Añadir puntos de oportunidad
                for _, row in oportunidades.iterrows():
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=10,
                        color='#3186cc',
                        fill=True,
                        fill_color='#3186cc',
                        popup=f"Clientes activos cercanos: {row['activos_cercanos']}"
                    ).add_to(m_oportunidades)
                
                # Añadir todos los puntos de alto potencial
                for _, row in alto_potencial.iterrows():
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='green',
                        fill=True,
                        fill_color='green'
                    ).add_to(m_oportunidades)
                
                st.components.v1.html(m_oportunidades._repr_html_(), height=400)
                
            else:
                st.warning("No se encontraron clusters significativos de leads potenciales.")
    else:
        st.warning("No hay datos de leads potenciales para analizar.")

# Opción para descargar datos consolidados
if st.button("Descargar Datos Consolidados"):
    csv = full_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar CSV",
        data=csv,
        file_name="datos_consolidados.csv",
        mime="text/csv"
    )
