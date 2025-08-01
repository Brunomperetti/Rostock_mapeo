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
        if uploaded_file is None:
            return None
            
        df = pd.read_excel(uploaded_file)
        
        # Estandariza los nombres de columnas
        column_mapping = {
            'lat': 'latitud',
            'lon': 'longitud',
            'Latitud': 'latitud',
            'Longitud': 'longitud',
            'Nombre': 'nombre',
            'Tipo': 'tipo',
            'Categoría': 'tipo',
            'Provincia': 'provincia',
            'Ciudad': 'localidad'
        }
        
        # Renombrar columnas
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Verificar columnas obligatorias
        required_columns = ['latitud', 'longitud']
        if not all(col in df.columns for col in required_columns):
            st.error(f"El archivo debe contener al menos las columnas: {', '.join(required_columns)}")
            return None
            
        # Asegurar que las coordenadas sean numéricas
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        
        # Eliminar filas sin coordenadas
        df = df.dropna(subset=['latitud', 'longitud'])
        
        # Crear columna 'tipo' si no existe
        if 'tipo' not in df.columns:
            df['tipo'] = 'Sin categorizar'
            
        return df

    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        return None

# Sidebar para carga de archivos
with st.sidebar:
    st.header("📤 Carga de Datos")
    uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"])
    
    if uploaded_file:
        df = load_data(uploaded_file)
    else:
        df = None
        st.warning("Por favor sube un archivo Excel")
        st.stop()

# Verificar si hay datos válidos
if df is None or df.empty:
    st.error("No se encontraron datos válidos para mostrar. Verifica el formato del archivo.")
    st.stop()

# Filtros (solo si hay datos)
with st.sidebar:
    st.header("⚙️ Filtros")
    
    # Opciones para los filtros
    tipos_disponibles = df['tipo'].unique().tolist() if 'tipo' in df.columns else ['Sin categorizar']
    provincias_disponibles = df['provincia'].unique().tolist() if 'provincia' in df.columns else ['Todas']
    
    # Widgets de filtro
    tipos_seleccionados = st.multiselect(
        "Tipos a mostrar:",
        options=tipos_disponibles,
        default=tipos_disponibles
    )
    
    provincias_seleccionadas = st.multiselect(
        "Provincias:",
        options=provincias_disponibles,
        default=provincias_disponibles
    )

# Aplicar filtros
df_filtrado = df.copy()
if 'tipo' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['tipo'].isin(tipos_seleccionados)]
if 'provincia' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['provincia'].isin(provincias_seleccionadas)]

# Crear mapa solo si hay datos filtrados
if not df_filtrado.empty:
    # Configurar colores
    color_discrete_map = {
        tipo: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, tipo in enumerate(df_filtrado['tipo'].unique())
    }
    
    # Crear figura
    fig = px.scatter_mapbox(
        df_filtrado,
        lat="latitud",
        lon="longitud",
        color="tipo",
        hover_name="nombre" if 'nombre' in df_filtrado.columns else None,
        hover_data=[col for col in ['provincia', 'localidad'] if col in df_filtrado.columns],
        zoom=4,
        height=700,
        color_discrete_map=color_discrete_map
    )

    # Configurar layout del mapa
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0, "t":0, "l":0, "b":0},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Mostrar mapa
    st.plotly_chart(fig, use_container_width=True)

    # Mostrar estadísticas
    with st.expander("📊 Estadísticas y Datos"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resumen por tipo:**")
            st.write(df_filtrado['tipo'].value_counts() if 'tipo' in df_filtrado.columns else "No hay datos de categorías")
            
        with col2:
            st.write("**Resumen por provincia:**")
            st.write(df_filtrado['provincia'].value_counts() if 'provincia' in df_filtrado.columns else "No hay datos de provincias")
        
        st.write("**Datos filtrados:**")
        st.dataframe(df_filtrado)

    # Botón para descargar
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar datos filtrados",
        data=csv,
        file_name="datos_filtrados.csv",
        mime="text/csv"
    )
else:
    st.warning("No hay datos que coincidan con los filtros seleccionados")
