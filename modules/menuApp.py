import streamlit as st
import pandas as pd
from modules import vincularCuentas, gestionDatos, visualizacionVAEP


def muestra_barra_lateral():
    st.sidebar.title('Barra de navegación')
    st.sidebar.markdown("---")

    paginas = {
        'Página principal': 'principal',
        'Vinculación de cuentas': 'vinculacion',
        'Gestión de datos': 'gestDatos',
        'Valoraciones VAEP': 'valVAEP'
    }

    idxActual = 0
    if 'pagActual' in st.session_state:
        try:
            idxActual = list(paginas.values()).index(st.session_state.pagActual)
        except ValueError:
            idxActual = 0

    pagseleccionada = st.sidebar.selectbox('Página', options = paginas.keys(), 
                    index = idxActual)
    
    nuevaPag = paginas[pagseleccionada]

    if 'pagActual' not in st.session_state or st.session_state.pagActual != nuevaPag:
        st.session_state.pagActual = nuevaPag
        st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.info(f'👤 {st.session_state.usuario}')
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        # Limpiar session state
        if st.session_state.recuerda:
            for key in list(st.session_state.keys()):
                if key not in ['recuerda', 'usuario', 'contrasena']:
                    del st.session_state[key]
        else:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        st.rerun()

def muestra_pantalla_principal():
    st.markdown("<h1 style='text-align: center'>¡Bienvenido a la aplicación de gestión de datos de eventing y valoración de jugadores!</h1>", unsafe_allow_html = True)
    st.markdown("""
                ### 📋 **Descripción General**

                Esta plataforma integra herramientas para la gestión, análisis y valoración de datos de 
                eventos deportivos, implementando el framework **VAEP** (Valuing Actions by Estimating Probabilities) 
                para la evaluación objetiva del rendimiento de jugadores de fútbol.    [Más información acerca de VAEP](https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/vaep.html)
                """)
    

    
    st.markdown("---")

    # Información de páginas
    st.markdown("### 🗺️ **Módulos de la Aplicación**")

    # Crear dos columnas para mejor organización
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 🔗 **Vinculación de Cuentas**
        Configuración de credenciales para acceso a APIs de datos deportivos.
        
        - Gestión de tokens de autenticación
        - Conexión con proveedores de datos (StatsBomb, Wyscout)
        - Validación de credenciales y permisos
        """)

    with col2:
        st.markdown("""
        #### 🗄️ **Gestión de Datos**
        Administración integral del pipeline de datos deportivos.
        
        - Descarga y procesamiento de datos en formato SPADL
        - Transformación de eventos de partidos
        - Exportación de datasets procesados
        """)
        
    with col3:
        st.markdown("""
        #### 📊 **Valoraciones VAEP**
        Análisis y visualización de valoraciones de acciones usando el framework VAEP.

        - Selección ajustable de partidos y competiciones concretos
        - Ranking de jugadores por su valoración VAEP
        - Visualización interactiva de acciones 
        """)

    st.markdown("---")

    # Footer con instrucciones
    st.markdown("""
    ### 🚀 **Instrucciones de uso**

    1. **Configura credenciales** en *Vinculación de cuentas* (si es necesario)
    2. **Procesa los datos** en *Gestión de datos* para preparar el dataset
    3. **Analiza rendimiento** en *Valoraciones VAEP* para obtener resultados
    """, unsafe_allow_html=True)

    st.markdown("""
                <div style='text-align: center; color: #666; font-size: 0.9em; margin-top: 2rem;'>
                <p style='margin-bottom: 0.2em;'>Aplicación desarrollada por Mateo Vera Murillo</p>
                <p style='margin-top: 0.2em;'>Grado en Ciencia de Datos de la Universidad Pública de Navarra</p>
                </div>
                """, unsafe_allow_html=True)


def muestra_menu_principal():
    muestra_barra_lateral()

    pagActual = st.session_state.pagActual

    if pagActual == 'principal':
        muestra_pantalla_principal()

    elif pagActual == 'vinculacion':
        vincularCuentas.muestra_pagina_credenciales()
        
    elif pagActual == 'valVAEP':
        visualizacionVAEP.muestra_pagina_visualizacion()

    elif pagActual == 'gestDatos':
        gestionDatos.muestra_pagina_gestionDatos()