import streamlit as st
import numpy as np
import pandas as pd
import pickle
import socceraction.spadl as spadl
import socceraction.vaep as vaep
import socceraction.vaep.features as fs
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import gc
import threading
import json
import shutil
import warnings
from statsbombpy.api_client import NoAuthWarning
warnings.simplefilter('ignore', NoAuthWarning)
warnings.filterwarnings('ignore', category=FutureWarning, module='socceraction')
warnings.filterwarnings('ignore', message='Inferred xy_fidelity_version.*')
warnings.filterwarnings('ignore', message='Inferred shot_fidelity_version.*')

MAX_WORKERS = 8


class Manager:
    def __init__(self, type, loader, dirBase):
        self.type = type
        self.loader = loader
        self.dirBase = Path(dirBase)
        self.dirBase.mkdir(exist_ok = True, parents = True)

        self.barraProgreso = None
        self.textoProgreso = None
        self.rango = None

        #Controla el caché de las competiciones y eventos, y el candado de acceso a la API
        self._competiciones_cache = None
        self.eventosCache = {}
        self._lock = threading.Lock()

        with open('models/modelo_scores.pkl', 'rb') as f:
            self.modeloScores = pickle.load(f)

        with open('models/modelo_concedes.pkl', 'rb') as f:
            self.modeloConcedes = pickle.load(f)

        self.xfns = [
            fs.actiontype,
            fs.bodypart_detailed,
            fs.endlocation,
            fs.endpolar,
            fs.goalscore,
            fs.movement,
            fs.player_possession_time,
            fs.result,
            fs.speed,
            fs.startlocation,
            fs.startpolar,
            fs.team,
            fs.time
        ]

        self.VAEP = vaep.VAEP(xfns = self.xfns, nb_prev_actions = 3)

        if self.type == 'Wyscout':
            self.posicionesWyscout = self.carga_posiciones_jugadores()


    def carga_posiciones_jugadores(self):
        with open('.temp/players.json', 'r', encoding='utf-8') as f:
            jugadores = json.load(f)
        
        return {
            jugador['wyId']: jugador.get('role', {}).get('name')
            for jugador in jugadores
            if 'wyId' in jugador
        }


    #Devuelve la lista de competiciones disponible en la api
    def get_competiciones(self):
        if self._competiciones_cache is None:
            archivoCache = self.dirBase / 'competiciones.pkl'

            if archivoCache.exists():
                try:
                    #Usamos with para que se cierre el archivo aunque haya habido errores en el proceso
                    with open(archivoCache, 'rb') as f:
                        self._competiciones_cache = pickle.load(f)
                    # self.logger.info(f'Competiciones cargadas desde caché: {len(self._competiciones_cache)}')
                    return self._competiciones_cache
                except:
                    pass
            
            competicionesAux = self.loader.competitions()
            if self.type == 'Wyscout':
                competicionesAux['competition_name'] = competicionesAux['competition_name'].replace({
                    'English first division': 'Premier League',
                    'French first division': 'Ligue 1',
                    'Spanish first division': 'La Liga',
                    'Italian first division': 'Serie A',
                    'German first division': '1. Bundesliga',
                    'European Championship': 'UEFA Euro',
                    'World Cup': 'FIFA World Cup'
                })

            self._competiciones_cache = competicionesAux.sort_values('competition_name')[['season_id', 'competition_id', 'competition_name', 'country_name',
                                                                                         'competition_gender', 'season_name']]

            with open(archivoCache, 'wb') as f:
                pickle.dump(self._competiciones_cache, f, protocol = pickle.HIGHEST_PROTOCOL)
            
            # self.logger.info(f'Se han encontrado {len(self._competiciones_cache)} competiciones')

        return self._competiciones_cache


    #Devuelve partidos de una competición y temporada concretas
    def get_partidos_concretos(self, idCompeticion, idTemporada):
        #No debería saltar error porque todas las competiciones tienen al menos un partido
        try:
            with self._lock:
                partidos = self.loader.games(competition_id = idCompeticion, season_id = idTemporada)
            return partidos
        except Exception as e:
            print(e)
            return pd.DataFrame()


    #Devuelve los eventos de un partido concreto en formato SPADL
    def get_eventos_partido_spadl(self, idPartido, idEquipoLocal):
        #Revisamos caché en primer lugar
        if idPartido in self.eventosCache:
            return self.eventosCache[idPartido]

        try:
            #El lock solo afecta a la llamada a la API, para acelerar la conversión a SPADL
            with self._lock:
                eventosSinFormato = self.loader.events(game_id = idPartido)

            if self.type == 'StatsBomb':
                eventos = spadl.statsbomb.convert_to_actions(
                    eventosSinFormato, 
                    home_team_id = idEquipoLocal
                )

            elif self.type == 'Wyscout':
                eventos = spadl.wyscout.convert_to_actions(
                    eventosSinFormato, 
                    home_team_id = idEquipoLocal
                )

            eventos = spadl.add_names(eventos)
            self.eventosCache[idPartido] = eventos
            return eventos
        
        except Exception as e:
            return pd.DataFrame()


    #Descarga eventos de todos los partidos en paralelo
    def descarga_eventos_paralelo(self, datosPartidos,maxWorkers = 1):
        eventosTodos = []
        numPartidos = len(datosPartidos)
        progresos = np.linspace(self.rango[0], self.rango[1], numPartidos + 1)
        cont = 0
    
        def coge_eventos_vaep(datosPartido):
            eventos = self.get_eventos_partido_spadl(datosPartido['game_id'], datosPartido['home_team_id'])
            eventosModelo = self.VAEP.compute_features(datosPartido, eventos)

            probScores = pd.Series(self.modeloScores.predict_proba(eventosModelo)[:, 1], name = 'Pscores')
            probConcedes = pd.Series(self.modeloConcedes.predict_proba(eventosModelo)[:, 1], name = 'Pconcedes')
            valoresVAEP = vaep.formula.value(eventos, probScores, probConcedes)
            
            return pd.concat([eventos, probScores, probConcedes, valoresVAEP], axis = 1)

    
        with ThreadPoolExecutor(max_workers = maxWorkers) as executor:
            #Diccionario que relaciona el future con los datos del partido
            futureAPartido = {
                executor.submit(coge_eventos_vaep, datosPartido): datosPartido['game_id']
                for _, datosPartido in datosPartidos.iterrows()
            }
                
            for future in as_completed(futureAPartido):
                idPartido = futureAPartido[future]

                try:
                    eventos = future.result(timeout = 30)
                    if not eventos.empty:
                        eventosTodos.append(eventos)

                except Exception as e:
                    print(e)
                    continue

                self.barraProgreso.progress(progresos[cont])
                cont += 1
    
        if eventosTodos:
           return pd.concat(eventosTodos, ignore_index = True)
        else:
            return pd.DataFrame()


    #Descarga y guarda en archivo una competición de una temporada concreta
    def guarda_competicion(self, idCompeticion, idTemporada, nombreCompeticion, nombreTemporada):
        dicPosiciones = {
        'Substitute': 'SUB',
        'Defender': 'DEF',
        'Midfielder': 'MC',
        'Forward': 'FW',
        'Right Midfield': 'RM',
        'Goalkeeper': 'G',
        'Center Midfield': 'CM',
        'Center Back': 'CB',
        'Center Defensive Midfield': 'CDM',
        'Left Center Midfield': 'LCM',
        'Left Midfield': 'LM',
        'Right Defensive Midfield': 'RDM',
        'Right Wing Back': 'RWB',
        'Left Back': 'LB',
        'Right Center Forward': 'RCF',
        'Secondary Striker': 'SS',
        'Left Defensive Midfield': 'LDM',
        'Left Center Forward': 'LCF',
        'Right Center Midfield': 'RCM',
        'Left Wing': 'LW',
        'Right Wing': 'RW',
        'Left Attacking Midfield': 'LAM',
        'Right Attacking Midfield': 'RAM',
        'Right Back': 'RB',
        'Right Center Back': 'RCB',
        'Left Wing Back': 'LWB',
        'Center Attacking Midfield': 'CAM',
        'Center Forward': 'CF',
        'Left Center Back': 'LCB'
        }
        
        #Crea un nombre limpio para el archivo, sin caracteres conflictivos ni espacios finales (rstrip)
        nombreCompetiLimpio = ''.join(c for c in nombreCompeticion if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nombreTempLimpio = ''.join(c for c in nombreTemporada if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nombreSubcarpeta = f'{nombreCompetiLimpio}_{nombreTempLimpio}'.replace(' ', '_')
        Path(self.dirBase / nombreSubcarpeta).mkdir(parents = True, exist_ok = True)
        rutaSubcarpeta = self.dirBase / nombreSubcarpeta

        rutaArchivoEventos = rutaSubcarpeta / 'eventos.pkl'
        rutaArchivoPartidos = rutaSubcarpeta / 'partidos.pkl'
        rutaArchivoEquipos = rutaSubcarpeta / 'equipos.pkl'
        rutaArchivoJugadores = rutaSubcarpeta / 'jugadores.pkl'

        #Se presupone que se ha cargado bien el eventing de la temporada
        if rutaArchivoEventos.exists():
            return
            
        print(f'\nProcesando: {nombreCompeticion} - {nombreTemporada}')

        #Obtiene los partidos del Loader
        dfPartidos = self.get_partidos_concretos(idCompeticion, idTemporada)

        if dfPartidos.empty:
            return

        #Obtiene los ids de los partidos, teniendo en cuenta las distintas casuísticas (el nombre puede variar según la versión de Socceraction), así como el id del equipo local
        #Obtiene también los equipos y jugadores participantes en los partidos
        equipos = pd.DataFrame(columns=['team_id', 'team_name'])
        jugadores = pd.DataFrame(columns = ['game_id', 'team_id', 'player_id', 'player_name', 
                                            'nickname', 'jersey_number', 'is_starter', 'starting_position_id', 
                                            'starting_position_name', 'minutes_played'])
        
        for indice, fila in dfPartidos.iterrows():
            if 'game_id' in dfPartidos.columns:
                idPartido = fila['game_id']
            elif 'match_id' in dfPartidos.columns:
                idPartido = fila['match_id']

            if self.type == 'Wyscout':
                datosPartido = self.loader._lineups(idPartido)
                dfPartidos.at[indice, 'home_score'] = int([dic['score'] for dic in datosPartido if dic['side'] == 'home'][0])
                dfPartidos.at[indice, 'away_score'] = int([dic['score'] for dic in datosPartido if dic['side'] == 'away'][0])

                if fila['game_day'] == 0:
                    dfPartidos.at[indice, 'competition_stage'] = 'Knockout Stage'
                else:
                    dfPartidos.at[indice, 'competition_stage'] = 'Group Stage'
     
                equipos = pd.concat([equipos, self.loader.teams(game_id = idPartido)[['team_id', 'team_name_short']].rename(columns = {'team_name_short': 'team_name'})], ignore_index = True)
                jugadoresPartido = self.loader.players(game_id = idPartido)
                jugadoresPartido['starting_position_name'] = jugadoresPartido['player_id'].map(self.posicionesWyscout)
                jugadores = pd.concat([jugadores, jugadoresPartido[[col for col in jugadores.columns if col != 'starting_position_id']]])
     
            elif self.type == 'StatsBomb':
                equipos = pd.concat([equipos, self.loader.teams(game_id = idPartido)], ignore_index = True)
                
                jugadores = pd.concat([jugadores, self.loader.players(game_id = idPartido)], ignore_index = True)
                
        equipos = equipos.drop_duplicates()
        if self.type == 'Wyscout':
            equipos['team_name'] = equipos['team_name'].apply(lambda x: x.encode().decode('unicode_escape'))

        jugadores['starting_position_name'] = jugadores['starting_position_name'].map(dicPosiciones)
        jugadores['player_name'] = jugadores['nickname'].fillna(jugadores['player_name'])
        jugadores = jugadores.drop('nickname', axis=1)
        jugadores = jugadores.merge(equipos, on='team_id', how='left')

        with open(rutaArchivoEquipos, 'wb') as f:
            pickle.dump(equipos, f, protocol = pickle.HIGHEST_PROTOCOL)

        with open(rutaArchivoJugadores, 'wb') as f:
            pickle.dump(jugadores.drop_duplicates(), f, protocol = pickle.HIGHEST_PROTOCOL)

        dfPartidos = dfPartidos.merge(equipos, left_on='home_team_id', right_on='team_id', how='left')
        dfPartidos = dfPartidos.merge(equipos, left_on='away_team_id', right_on='team_id', how='left', suffixes=('_home', '_away'))

        dfPartidos['result'] = dfPartidos['team_name_home'] + ' ' + dfPartidos['home_score'].astype(int).astype(str) + ' - ' + dfPartidos['away_score'].astype(int).astype(str) + ' ' + dfPartidos['team_name_away']
        dfPartidos = dfPartidos.drop(['team_id_home', 'team_id_away'], axis=1)

        print(f'Total de partidos a procesar: {len(dfPartidos)}')

        with open(rutaArchivoPartidos, 'wb') as f:
            pickle.dump(dfPartidos, f, protocol = pickle.HIGHEST_PROTOCOL)

        tInic = time.time()

        print(f'Descargando eventos con {MAX_WORKERS} workers en paralelo')
        dfEventosTodos = self.descarga_eventos_paralelo(dfPartidos, maxWorkers = MAX_WORKERS)

        dfEventosTodos = dfEventosTodos.merge(dfPartidos[['game_id', 'competition_stage', 'game_day', 'result']], on='game_id', how='left')
        dfEventosTodos = dfEventosTodos.merge(equipos, on='team_id', how='left')
        dfEventosTodos = dfEventosTodos.merge(jugadores[['player_id', 'player_name']].drop_duplicates(), on='player_id', how='left')

        tDescarga = time.time() - tInic

        if dfEventosTodos.empty:
            return

        # Procesa y guarda los eventos recibidos
        with open(rutaArchivoEventos, 'wb') as f:
            pickle.dump(dfEventosTodos, f, protocol = pickle.HIGHEST_PROTOCOL)
            
        # Muestra la información final
        tamanoArchivoMB = rutaArchivoEventos.stat().st_size / (1024 ** 2)
        partidosSeg = len(dfPartidos) / tDescarga if tDescarga > 0 else 0
        
        print(f'{nombreSubcarpeta} guardado:')
        print(f'{len(dfEventosTodos):,} eventos')
        print(f'{tamanoArchivoMB:.2f} MB')
        print(f'{tDescarga:.1f} segundos')
        print(f'{partidosSeg:.1f} partidos/segundo')
        
        # Limpia caché si es muy grande
        if len(self.eventosCache) > 1000:
            self.eventosCache.clear()

        #Libera memoria
        del dfEventosTodos, equipos, jugadores, dfPartidos
        gc.collect()



    #Descarga todas las competiciones disponibles en el Loader
    def descarga_todas_competiciones(self):
        self.muestra_progreso_descarga()
        dfCompeticiones = self.get_competiciones()

        numCompeticiones = len(dfCompeticiones)
        salto = 1 / numCompeticiones
        self.rango += np.array([0, salto], dtype = float)
        cont = 1

        for _, fila in dfCompeticiones.iterrows():
            nombreCompeticion = fila['competition_name']
            nombreTemporada = fila['season_name']
            
            self.textoProgreso.text(f'Descargando {nombreCompeticion} de {nombreTemporada}')

            self.guarda_competicion(
                idCompeticion = fila['competition_id'],
                idTemporada = fila['season_id'],
                nombreCompeticion = nombreCompeticion,
                nombreTemporada = nombreTemporada
            )

            self.rango += np.array([salto] * 2)

        self.barraProgreso.progress(1.0)

        if numCompeticiones > 1:
            self.textoProgreso.text(f'Se han descargado {numCompeticiones} competiciones.')

        elif numCompeticiones == 1:
            self.textoProgreso.text(f'Se ha descargado una competición.')
        
        time.sleep(3)
        st.rerun()


    #Descarga competiciones concretas basándose en ids o nombres
    def descarga_competiciones_concretas(self, filtrosCompeticiones):
        self.muestra_progreso_descarga()
        dfCompeticiones = self.get_competiciones()
        competicionesADescargar = []

        for dicFiltros in filtrosCompeticiones:
            mascara = pd.Series([True] * len(dfCompeticiones))
            for clave, valor in dicFiltros.items():
                if clave in dfCompeticiones.columns:
                    mascara &= (dfCompeticiones[clave] == valor)

            competicionesFiltradas = dfCompeticiones[mascara]

            if competicionesFiltradas.empty:
                continue

            for _, fila in competicionesFiltradas.iterrows():
                competicionesADescargar.append(fila)

        if not competicionesADescargar:
            print('No se encontraron competiciones para descargar')
            return

        numCompeticiones = len(competicionesADescargar)
        salto = 1 / numCompeticiones
        self.rango += np.array([0, salto], dtype = float)

        for fila in competicionesADescargar:
            nombreCompeticion = fila['competition_name']
            nombreTemporada = fila['season_name']

            self.textoProgreso.text(f'Descargando {nombreCompeticion} de {nombreTemporada}')

            self.guarda_competicion(
                idCompeticion = fila['competition_id'],
                idTemporada = fila['season_id'],
                nombreCompeticion = nombreCompeticion,
                nombreTemporada = nombreTemporada
            )
            self.rango += np.array([salto] * 2)

        self.barraProgreso.progress(1.0)

        if numCompeticiones > 1:
            self.textoProgreso.text(f'Se han descargado {numCompeticiones} competiciones.')

        elif numCompeticiones == 1:
            self.textoProgreso.text(f'Se ha descargado una competición.')

        time.sleep(3)
        st.rerun()


    #Obtiene la ruta del archivo de la competición en cuestión
    def get_carpeta_competicion(self, nombreCompeticion, nombreTemporada):
        nombreCompetiLimpio = ''.join(c for c in nombreCompeticion if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nombreTempLimpio = ''.join(c for c in nombreTemporada if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nombreSubcarpeta = f'{nombreCompetiLimpio}_{nombreTempLimpio}'.replace(' ', '_')
        return self.dirBase / nombreSubcarpeta
    
    
    def borra_competicion(self, nombreCompeticion, nombreTemporada):
        ruta = self.get_carpeta_competicion(nombreCompeticion, nombreTemporada)
        
        if ruta.exists():
            shutil.rmtree(ruta)

    
    #Elimina las competiciones indicadas en el filtro
    def borra_competicion_concreta(self, filtrosCompeticiones):
        self.muestra_proceso_borrado()

        dfCompeticiones = self.get_competiciones()
        competicionesABorrar = []

        for dicFiltros in filtrosCompeticiones:
            mascara = pd.Series([True] * len(dfCompeticiones))
            for clave, valor in dicFiltros.items():
                if clave in dfCompeticiones.columns:
                    mascara &= (dfCompeticiones[clave] == valor)

            competicionesFiltradas = dfCompeticiones[mascara]

            for _, fila in competicionesFiltradas.iterrows():
                competicionesABorrar.append(fila)

        numCompeticiones = len(competicionesABorrar)
        cont = 1

        for fila in competicionesABorrar:
            nombreCompeticion = fila['competition_name']
            nombreTemporada = fila['season_name']

            self.barraProgreso.progress(cont / numCompeticiones)
            self.textoProgreso.text(f'Borrando {nombreCompeticion} de {nombreTemporada}')

            self.borra_competicion(
                nombreCompeticion,
                nombreTemporada
            )
            cont += 1

        self.barraProgreso.progress(1.0)

        if numCompeticiones > 1:
            self.textoProgreso.text(f'Se han eliminado {numCompeticiones} competiciones.')

        elif numCompeticiones == 1:
            self.textoProgreso.text('Se ha eliminado 1 competición.')      

        time.sleep(3)
        st.rerun()


    #Borra todas las competiciones guardadas en la carpeta local
    def borra_todas_competiciones(self):
        self.muestra_proceso_borrado()
        numArchivos = len(os.listdir(self.dirBase))
        cont = 1
        for carpeta in self.dirBase.iterdir():
            if carpeta.is_dir():
                prog = cont / numArchivos
                self.barraProgreso.progress(prog)
                self.textoProgreso.text(f'Borrando carpeta {str(carpeta)}')
                shutil.rmtree(carpeta)
                cont += 1

        self.barraProgreso.progress(1.0)

        self.textoProgreso.text(f'Todas las competiciones disponibles han sido eliminadas.')

        time.sleep(3)
        st.rerun()


    #Carga los datos de una competición concreta
    def carga_datos_competicion(self, nombreCompeticion, nombreTemporada):
        ruta = self.get_carpeta_competicion(nombreCompeticion, nombreTemporada)
        
        with open(ruta / 'eventos.pkl', 'rb') as f:
            eventos =  pickle.load(f)

        with open(ruta / 'partidos.pkl', 'rb') as f:
            partidos =  pickle.load(f)

        with open(ruta / 'equipos.pkl', 'rb') as f:
            equipos =  pickle.load(f)

        with open(ruta / 'jugadores.pkl', 'rb') as f:
            jugadores =  pickle.load(f)

        return eventos, partidos, equipos, jugadores

    #Devuelve una lista con las competiciones ya descargadas
    def lista_competiciones_descargadas(self):
        lista = []
        for carpeta in self.dirBase.iterdir():
            if carpeta.is_dir():
                nombre = carpeta.name.replace('_', ' ')

                if 'Bundesliga' in nombre:
                        nombre = nombre.replace('1 ', '1. ')

                if nombre[-8:].isnumeric():
                    nombre = nombre[:-4] + '/' + nombre[-4:]
                    
                lista.append(nombre)
        return lista



    #Devuelve información del estado de las competiciones
    def get_info_competiciones(self):
        competiciones = self.get_competiciones()

        competiciones['Descargada'] = competiciones.apply(
            lambda fila: 'Sí' if self.get_carpeta_competicion(
                    fila['competition_name'],
                    fila['season_name']
            ).exists() else 'No', axis = 1
        )

        return competiciones
    

    @st.dialog('Descarga en proceso', dismissible = False)
    def muestra_progreso_descarga(self):
        self.barraProgreso = st.progress(0)
        self.textoProgreso = st.empty()
        self.rango = np.array([0, 0], dtype = float)


    @st.dialog('Borrado en proceso', dismissible = False)
    def muestra_proceso_borrado(self):
        self.barraProgreso = st.progress(0)
        self.textoProgreso = st.empty()
        self.rango = np.array([0, 0], dtype = float)

