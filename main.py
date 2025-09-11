import streamlit as st
import pickle
import requests
import io
from modules import controlLogin, menuApp

st.set_page_config(
    page_title = 'App TFG',
    page_icon = '⚽',
    layout = 'wide'
)

def main():
    with open('login_data/login.pkl', 'rb') as f:
        st.session_state.dfLogin = pickle.load(f)

    if 'loggeado' not in st.session_state:
        st.session_state.loggeado = False

    if st.session_state.loggeado:
        menuApp.muestra_menu_principal()
        
    else:
        controlLogin.muestra_pagina_login()


if __name__ == '__main__':
    main()