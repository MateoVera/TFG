import streamlit as st
from modules import manager
from socceraction.data.statsbomb import StatsBombLoader
from socceraction.data.wyscout import PublicWyscoutLoader
import numpy as np
from pathlib import Path
import os
import platform
import time
import pickle

@st.dialog('Cuenta no vinculada', width = 'medium', on_dismiss = 'rerun')
def muestra_mensaje_invitado(opcion):
    if opcion == 1:
        st.info('Se ha seleccionado por defecto la cuenta de invitado. Puedes cambiar a tu cuenta personal de StatsBomb desde **Vinculación de cuentas**.')

    elif opcion == 2:
        st.info('Se ha seleccionado por defecto la cuenta de invitado. Puedes cambiar a tu cuenta personal de Wyscout desde **Vinculación de cuentas**.')

    else:
        st.info('Se han seleccionado por defecto las cuentas de invitado. Puedes cambiar a tus cuentas personales de StatsBomb y Wyscout desde **Vinculación de cuentas**.')

def muestra_pagina_gestionDatos():
    invitadoSB = False 
    invitadoW = False
    pestanaStatsBomb, pestanaWyscout = st.tabs(['StatsBomb', 'Wyscout'])

    if not st.session_state.credsStatsBomb:
            st.session_state.credsStatsBomb = StatsBombLoader(getter = 'remote', creds = {'user': None, 'passwd': None})
            st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsStatsBomb'] = st.session_state.credsStatsBomb

            with open('login_data/login.pkl', 'wb') as f:
                pickle.dump(st.session_state.dfLogin, f)

            invitadoSB = True

    if not st.session_state.credsWyscout:
            ruta = Path('.temp')
            ruta.mkdir(exist_ok = True)

            if platform.system() == 'Windows':
                os.system(f'attrib +h "{ruta}"')

            st.session_state.credsWyscout = PublicWyscoutLoader(root = ruta)
            st.session_state.dfLogin.loc[st.session_state.dfLogin['usuario'] == st.session_state.usuario, 'credsWyscout'] = st.session_state.credsWyscout
           
            with open('login_data/login.pkl', 'wb') as f:
                pickle.dump(st.session_state.dfLogin, f)

            invitadoW = True

    if invitadoSB and invitadoW:
        muestra_mensaje_invitado(3)

    elif invitadoSB:
        muestra_mensaje_invitado(1)

    elif invitadoW:
        muestra_mensaje_invitado(2)

    with pestanaStatsBomb:        
        if not st.session_state.manSB:
            st.session_state.manSB = manager.Manager(type = 'StatsBomb', loader = st.session_state.credsStatsBomb, dirBase = 'data/statsbomb_data')

        st.markdown("<h1 style='text-align: center'> Gestión de datos de StatsBomb </h1>", unsafe_allow_html = True)

        competisDisponibles = st.session_state.manSB.get_info_competiciones().copy()
        seleccion = st.dataframe(
            data = competisDisponibles,
            hide_index = True,
            on_select = 'rerun',
            selection_mode = 'multi-row',
            key = 'selecSB'
        )

        competisSelec = competisDisponibles.iloc[seleccion.selection.rows]

        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            descParcial = st.button(f'Descargar {len(competisSelec)} competiciones', use_container_width = True, disabled = (len(competisSelec) == 0))
        with c2:
            descTotal = st.button('Descargar todas las competiciones', use_container_width = True)
        with c3:
            borrParcial = st.button(f'Borrar {len(competisSelec)} competiciones', use_container_width = True, disabled = (len(competisSelec) == 0))
        with c4:
            borrTotal = st.button('Borrar todas las competiciones', use_container_width = True)


        if descParcial or descTotal:
            tInic = time.time()
            if descTotal:
                competisSelec = competisDisponibles

            cantidadYaDescargada = np.sum(competisSelec['Descargada'] == 'Sí')

            if cantidadYaDescargada == len(competisSelec):
                st.info('ℹ️ Todas las competiciones seleccionadas ya han sido descargadas previamente. Para sobrescribirlas, bórralas previamente.')
                time.sleep(2)
            else:
                if cantidadYaDescargada > 0:
                    st.info('ℹ️ Algunas de las competiciones seleccionadas ya han sido descargadas previamente. Para sobrescribirlas, bórralas previamente.')
                    time.sleep(2)
                    competisADescargar = competisSelec.loc[competisSelec['Descargada'] == 'No']
                else:
                    competisADescargar = competisSelec

                if descParcial:
                    filtrosCompetis = []

                    for _, fila in competisADescargar.iterrows():
                        filtrosCompetis.append({
                            'competition_id': fila['competition_id'],
                            'season_id': fila['season_id']
                        })

                    st.session_state.manSB.descarga_competiciones_concretas(filtrosCompetis)
                
                else:
                    st.session_state.manSB.descarga_todas_competiciones()
                    
            st.rerun()

        if borrParcial or borrTotal:
            if borrTotal:
                competisSelec = competisDisponibles
            
            cantidadNoDescargada = np.sum(competisSelec['Descargada'] == 'No')

            if cantidadNoDescargada == len(competisSelec):
                st.info('ℹ️ No se ha encontrado ninguna de las competiciones seleccionadas en la carpeta local.')
                time.sleep(2)

            else:
                if cantidadNoDescargada > 0:
                    st.info('ℹ️ Alguna de las competiciones seleccionadas no se ha encontrado en la carpeta local.')
                    time.sleep(2)
                    competisABorrar = competisSelec.loc[competisSelec['Descargada'] == 'Sí']

                else:
                    competisABorrar = competisSelec

                if borrParcial:
                    filtrosCompetis = []

                    for _, fila in competisABorrar.iterrows():
                        filtrosCompetis.append({
                            'competition_id': fila['competition_id'],
                            'season_id': fila['season_id']
                        })

                    st.session_state.manSB.borra_competicion_concreta(filtrosCompetis)

                else:
                    st.session_state.manSB.borra_todas_competiciones()
                
            st.rerun()

    with pestanaWyscout:       
        if not st.session_state.manW:
            st.session_state.manW = manager.Manager(type = 'Wyscout', loader = st.session_state.credsWyscout, dirBase = 'data/wyscout_data')


        st.markdown("<h1 style='text-align: center'> Gestión de datos de Wyscout </h1>", unsafe_allow_html = True)

        competisDisponibles = st.session_state.manW.get_info_competiciones().copy()
        seleccion = st.dataframe(
            data = competisDisponibles,
            hide_index = True,
            on_select = 'rerun',
            selection_mode = 'multi-row',
            key = 'selecW'
        )

        competisSelec = competisDisponibles.iloc[seleccion.selection.rows]

        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            descParcial = st.button(f'Descargar {len(competisSelec)} competiciones', 
                                    use_container_width = True, disabled = (len(competisSelec) == 0), key = 'botonW1')
        with c2:
            descTotal = st.button('Descargar todas las competiciones', use_container_width = True, key = 'botonW2')
        with c3:
            borrParcial = st.button(f'Borrar {len(competisSelec)} competiciones', 
                                    use_container_width = True, disabled = (len(competisSelec) == 0), key = 'botonW3')
        with c4:
            borrTotal = st.button('Borrar todas las competiciones', use_container_width = True, key = 'botonW4')


        if descParcial or descTotal:
            if descTotal:
                competisSelec = competisDisponibles

            cantidadYaDescargada = np.sum(competisSelec['Descargada'] == 'Sí')

            if cantidadYaDescargada == len(competisSelec):
                st.info('ℹ️ Todas las competiciones seleccionadas ya han sido descargadas previamente. Para sobrescribirlas, bórralas previamente.')
            else:
                if cantidadYaDescargada > 0:
                    st.info('ℹ️ Algunas de las competiciones seleccionadas ya han sido descargadas previamente. Para sobrescribirlas, bórralas previamente.')
                    competisADescargar = competisSelec.loc[competisSelec['Descargada'] == 'No']
                else:
                    competisADescargar = competisSelec

                if descParcial:
                    filtrosCompetis = []

                    for _, fila in competisADescargar.iterrows():
                        filtrosCompetis.append({
                            'competition_id': fila['competition_id'],
                            'season_id': fila['season_id']
                        })

                    st.session_state.manW.descarga_competiciones_concretas(filtrosCompetis)
                
                else:
                    st.session_state.manW.descarga_todas_competiciones()
                    
                st.rerun()

        if borrParcial or borrTotal:
            if borrTotal:
                competisSelec = competisDisponibles
            
            cantidadNoDescargada = np.sum(competisSelec['Descargada'] == 'No')

            if cantidadNoDescargada == len(competisSelec):
                st.info('ℹ️ No se ha encontrado ninguna de las competiciones seleccionadas en la carpeta correspondiente.')

            else:
                if cantidadNoDescargada > 0:
                    st.info('ℹ️ Alguna de las competiciones seleccionadas no se ha encontrado en la carpeta correspondiente.')
                    competisABorrar = competisSelec.loc[competisSelec['Descargada'] == 'Sí']

                else:
                    competisABorrar = competisSelec

                if borrParcial:
                    filtrosCompetis = []

                    for _, fila in competisABorrar.iterrows():
                        filtrosCompetis.append({
                            'competition_id': fila['competition_id'],
                            'season_id': fila['season_id']
                        })

                    st.session_state.manW.borra_competicion_concreta(filtrosCompetis)

                else:
                    st.session_state.manW.borra_todas_competiciones()
                
                st.rerun()
