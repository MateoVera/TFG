import streamlit as st
from cryptography.fernet import Fernet
import pickle
from modules import manager


def decodifica_contrasena(contrasenaCodificada):
    with open('login_data/.clave.pkl', 'rb') as f:
        clave = pickle.load(f)
    # st.secrets['CLAVE'] = clave

    cipher = Fernet(clave)
    return cipher.decrypt(contrasenaCodificada).decode()

def comprueba_credenciales(usuario, contrasena):
    if usuario in st.session_state.dfLogin['usuario'].values:
        if contrasena == decodifica_contrasena(st.session_state.dfLogin[st.session_state.dfLogin['usuario'] == usuario]['contrasena'].iloc[0]):
            return True
    return False

# def obtiene_permisos(usuario):
#     return [clave for clave, valor in PERMISOS.items() if usuario in valor]

def muestra_pagina_login():
    
    # Título y subtítulo
    st.markdown("<h1 style='text-align: center'>Aplicación de gestión de datos y valoración de jugadores</h1>", unsafe_allow_html = True)
    st.markdown("<h2 style='text-align: center'>Inicio de sesión</h2>", unsafe_allow_html = True)
    st.markdown("<p style='text-align: center'>Introduce tus credenciales para acceder a la aplicación.<br>En caso de no tener, accede como invitado.</p>", unsafe_allow_html = True)

    

    with st.form('inicioSesion'):
        st.subheader('Credenciales')

        if True in st.session_state.dfLogin['recuerda'].values:
            usuario = st.text_input('👤 Usuario', value = st.session_state.dfLogin[st.session_state.dfLogin['recuerda'] == True]['usuario'].iloc[0], 
                                    placeholder = 'Introduce tu nombre de usuario')
            contrasena = st.text_input('🔒 Contraseña', value = decodifica_contrasena(st.session_state.dfLogin[st.session_state.dfLogin['recuerda'] == True]['contrasena'].iloc[0]), 
                                       placeholder = 'Introduce tu contraseña', type = 'password')
        else:
            usuario = st.text_input('👤 Usuario', placeholder = 'Introduce tu nombre de usuario')
            contrasena = st.text_input('🔒 Contraseña', placeholder = 'Introduce tu contraseña', type = 'password')

        recuerda = st.checkbox('Recuérdame', value = True)

        # Botones en columnas
        col1, col2 = st.columns(2)

        with col1: 
            botonEnvio = st.form_submit_button('Iniciar sesión', type = 'primary', use_container_width = True)
        with col2: 
            botonInvitado = st.form_submit_button('Acceder como invitado', type = 'secondary', use_container_width = True)

        if botonEnvio:
            if usuario and contrasena:
                if comprueba_credenciales(usuario, contrasena):
                    st.session_state.loggeado = True
                    st.session_state.usuario = usuario
                    st.session_state.recuerda = recuerda

                    if recuerda:
                        st.session_state.dfLogin['recuerda'] = st.session_state.dfLogin['usuario'] == usuario
                    else:
                        st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == usuario, 'recuerda'] = False

                    with open('login_data/login.pkl', 'wb') as f:
                        pickle.dump(st.session_state.dfLogin, f)

                    st.session_state.credsStatsBomb = st.session_state.dfLogin[st.session_state.dfLogin['usuario'] == usuario]['credsStatsBomb'].iloc[0]
                    st.session_state.credsWyscout = st.session_state.dfLogin[st.session_state.dfLogin['usuario'] == usuario]['credsWyscout'].iloc[0]
                    if st.session_state.credsStatsBomb:
                        st.session_state.manSB = manager.Manager(type = 'StatsBomb', loader = st.session_state.credsStatsBomb, dirBase = 'data/statsbomb_data')

                    if st.session_state.credsWyscout:
                        st.session_state.manW = manager.Manager(type = 'Wyscout', loader = st.session_state.credsWyscout, dirBase = 'data/wyscout_data')

                    st.success('✅ Inicio de sesión exitoso. Redirigiendo...')
                    st.rerun()
                else:
                    st.error('❌ Usuario y/o contraseña incorrectos')
            else:
                st.warning('⚠️ Por favor, completa todos los campos')

        elif botonInvitado:
            st.session_state.loggeado = True
            st.session_state.usuario = 'invitado'
            st.session_state.contrasena = None
            st.session_state.recuerda = False

            st.session_state.credsStatsBomb = st.session_state.dfLogin[st.session_state.dfLogin['usuario'] == 'invitado']['credsStatsBomb'].iloc[0]
            st.session_state.credsWyscout = st.session_state.dfLogin[st.session_state.dfLogin['usuario'] == 'invitado']['credsWyscout'].iloc[0]

            st.session_state.manSB = manager.Manager(type = 'StatsBomb', loader = st.session_state.credsStatsBomb, dirBase = 'data/statsbomb_data')
            st.session_state.manW = manager.Manager(type = 'Wyscout', loader = st.session_state.credsWyscout, dirBase = 'data/wyscout_data')

            # st.session_state.permisos = obtiene_permisos('invitado')
            st.success('✅ Accediendo como invitado. Redirigiendo...')
            st.rerun()


