import streamlit as st
from statsbombpy.config import HOSTNAME, VERSIONS
import requests as req
import pickle
from wyscoutapi import WyscoutAPI
from socceraction.data.statsbomb import StatsBombLoader
from socceraction.data.wyscout import PublicWyscoutLoader
# from modules import github
import platform
import os
from pathlib import Path


def muestra_pagina_credenciales():
    st.markdown("<h1 style='text-align: center'> Vinculación de credenciales </h1>", unsafe_allow_html = True)
    st.markdown("<h3 style='text-align: center'> Inicia sesión en las principales plataformas de análisis deportivo para descargar sus datos.</h3>", unsafe_allow_html = True)
    st.markdown("<p style='text-align: center'> Si no dispones de cuenta, solo tendrás acceso a los datos del usuario público.</p>", unsafe_allow_html = True)

    with st.expander('StatsBomb'):
        if not st.session_state.credsStatsBomb:
            with st.form('Vincula tu cuenta de StatsBomb'):
                usuario = st.text_input('👤 Usuario', placeholder = 'Introduce tu nombre de usuario')
                contrasena = st.text_input('🔒 Contraseña', placeholder = 'Introduce tu contraseña', type = 'password')
                botonStatsBomb = st.form_submit_button('Vincular cuenta')
            if botonStatsBomb:
                if usuario == '' and contrasena == '':
                    st.success('✅ Cuenta vinculada correctamente.')
                    st.session_state.credsStatsBomb = StatsBombLoader(getter = 'remote', creds = {'user': None, 'passwd': None})
                    st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsStatsBomb'] = st.session_state.credsStatsBomb

                    with open('login_data/login.pkl', 'wb') as f:
                            pickle.dump(st.session_state.dfLogin, f)
                        # github.sube_a_github()

                    st.rerun()

                else:
                    resp = req.get(f'{HOSTNAME}/api/{VERSIONS['competitions']}/competitions', 
                                auth = req.auth.HTTPBasicAuth(usuario, contrasena))
                    if resp.status_code != 200:
                        st.error('❌ Usuario y/o contraseña incorrectos.')
                    else:
                        st.success('✅ Cuenta vinculada correctamente.')
                        st.session_state.credsStatsBomb = StatsBombLoader(getter = 'remote', creds = {'user': usuario, 'passwd': contrasena})
                        st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsStatsBomb'] = st.session_state.credsStatsBomb

                        with open('login_data/login.pkl', 'wb') as f:
                            pickle.dump(st.session_state.dfLogin, f)
                        # github.sube_a_github()

                        st.rerun()

        else:
            if st.session_state.usuario == 'invitado':
                st.info('✅ Este usuario ya tiene una cuenta de StatsBomb vinculada.')
                st.info('Como has iniciado sesión como invitado, solo tienes acceso a la cuenta de invitado de StatsBomb.')

            else:
                st.info('✅ Este usuario ya tiene una cuenta de StatsBomb vinculada.')
                if st.button('Cambiar de cuenta', key = 'cambioCuentaSb'):
                    st.session_state.credsStatsBomb = None
                    st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsStatsBomb'] = None
                    with open('login_data/login.pkl', 'wb') as f:
                        pickle.dump(st.session_state.dfLogin, f)
                    st.rerun()

    with st.expander('Wyscout'):
        if not st.session_state.credsWyscout:
            with st.form('Vincula tu cuenta de Wyscout'):
                usuario2 = st.text_input('👤 Usuario', placeholder = 'Introduce tu nombre de usuario')
                contrasena2 = st.text_input('🔒 Contraseña', placeholder = 'Introduce tu contraseña', type = 'password')
                botonWyscout = st.form_submit_button('Vincular cuenta')
            if botonWyscout:
                if usuario2 == '' and contrasena2 == '':
                    st.success('✅ Cuenta vinculada correctamente.')
                    ruta = Path('.temp')
                    ruta.mkdir(exist_ok = True)

                    if platform.system() == 'Windows':
                        os.system(f'attrib +h "{ruta}"')
                    st.session_state.credsWyscout = PublicWyscoutLoader(root = ruta)
                    st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsWyscout'] = st.session_state.credsWyscout
                    with open('login_data/login.pkl', 'wb') as f:
                            pickle.dump(st.session_state.dfLogin, f)
                    
                    st.rerun()
                    
                else:
                    try:
                        WyscoutAPI(username = usuario2, password = contrasena2).areas()
                        st.success('✅ Cuenta vinculada correctamente.')
                        st.session_state.credsWyscout = WyscoutAPI(username = usuario2, password = contrasena2)
                        st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsWyscout'] = st.session_state.credsWyscout
           
                        with open('login_data/login.pkl', 'wb') as f:
                            pickle.dump(st.session_state.dfLogin, f)
                        # github.sube_a_github()

                        st.rerun()
                        
                    except:
                        st.error('❌ Usuario y/o contraseña incorrectos.')
        else:
            if st.session_state.usuario == 'invitado':
                st.info('✅ Este usuario ya tiene una cuenta de StatsBomb vinculada.')
                st.info('Como has iniciado sesión como invitado, solo tienes acceso a la cuenta de invitado de StatsBomb.')

            else:
                st.info('✅ Este usuario ya tiene una cuenta de Wyscout vinculada.')
                if st.button('Cambiar de cuenta', key = 'cambioCuentaW'):
                    st.session_state.credsWyscout = None
                    st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsWyscout'] = None
                    with open('login_data/login.pkl', 'wb') as f:
                        pickle.dump(st.session_state.dfLogin, f)
                    st.rerun()

