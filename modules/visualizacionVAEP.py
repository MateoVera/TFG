import streamlit as st
import pandas as pd
from pathlib import Path
from modules import manager
import numpy as np
import matplotsoccer as mps
import matplotlib.pyplot as plt
import math
import itertools
from matplotlib.pyplot import cm

HELP = 'Substitute -> SUB;   Right Midfield -> RM;   Goalkeeper -> G;   Center Midfield -> CM;   Center Back -> CB;   Center Defensive Midfield -> CDM;   Left Center Midfield -> LCM;   Left Midfield -> LM;   Right Defensive Midfield -> RDM;   Right Wing Back -> RWB;   Left Back -> LB;   Right Center Forward -> RCF;   Secondary Striker -> SS;   Left Defensive Midfield -> LDM;   Left Center Forward -> LCF;   Right Center Midfield -> RCM;   Left Wing -> LW;   Right Wing -> RW;   Left Attacking Midfield -> LAM;   Right Attacking Midfield -> RAM;   Right Back -> RB;   Right Center Back -> RCB;   Left Wing Back -> LWB;   Center Attacking Midfield -> CAM;   Center Forward -> CF;   Left Center Back -> LCB'
spadl_config = {
    "length": 105,
    "width": 68,
    "penalty_box_length": 16.5,
    "penalty_box_width": 40.3,
    "six_yard_box_length": 5.5,
    "six_yard_box_width": 18.3,
    "penalty_spot_distance": 11,
    "goal_width": 7.3,
    "goal_length": 2,
    "origin_x": 0,
    "origin_y": 0,
    "circle_radius": 9.15,
}
zaction = 9000

def filtra_eventos(eventos, fase = None, jornada = None, partido = None, equipo = None, tipo = None):
    eventosFiltrados = eventos
    if partido:
        eventosFiltrados = eventosFiltrados[eventosFiltrados['result'] == partido]
    elif jornada:
        eventosFiltrados = eventosFiltrados[eventosFiltrados['game_day'] == jornada]
    if fase:
        eventosFiltrados = eventosFiltrados[eventosFiltrados['competition_stage'] == fase]
    
    if equipo:
        eventosFiltrados = eventosFiltrados[eventosFiltrados['team_name'] == equipo]

    return eventosFiltrados


def calcula_vaep(eventos, jugadores, verbose=False):
    # Determinar nivel de agregación
    numPartidos = eventos['game_id'].nunique()
    numJornadas = eventos['game_day'].nunique()

    if numPartidos == 1:
        grupoCols = ['Nombre', 'Equipo', 'Posición Inicial']
    elif numJornadas == 1:
        grupoCols = ['Nombre', 'Equipo']
    else:
        grupoCols = ['Nombre']

    # Calcula VAEP por jugador-partido
    filas = []
    for partidoId in eventos['game_id'].unique():
        eventosPartido = eventos[eventos['game_id'] == partidoId]
        jugadoresPartido = jugadores[jugadores['game_id'] == partidoId]
        equiposPartido = eventos['team_name'].unique()
        
        for jugadorId in eventosPartido['player_id'].unique():
            jugadorInfo = jugadoresPartido[jugadoresPartido['player_id'] == jugadorId]

            if jugadorInfo.empty:
                continue

            if jugadorInfo['team_name'].iloc[0] in equiposPartido:
                vaepJugador = eventosPartido[eventosPartido['player_id'] == jugadorId]['vaep_value'].sum()
                
                filas.append({
                    'Nombre': jugadorInfo['player_name'].iloc[0],
                    'Equipo': jugadorInfo['team_name'].iloc[0],
                    'Posición Inicial': jugadorInfo['starting_position_name'].iloc[0],
                    'Minutos Jugados': jugadorInfo['minutes_played'].iloc[0],
                    'VAEP': vaepJugador
                })

    df = pd.DataFrame(filas)

    # Agregar según el nivel
    if len(grupoCols) < 3:  # Necesita agregación
        aggDic = {
            'Minutos Jugados': 'sum',
            'VAEP': 'sum'
        }
        
        if 'Equipo' in grupoCols:
            aggDic['Posición Inicial'] = lambda x: ', '.join(sorted(x.unique()))
        else:
            aggDic['Equipo'] = lambda x: ', '.join(sorted(x.unique()))
            aggDic['Posición Inicial'] = lambda x: ', '.join(sorted(set([pos.strip() for fila in x for pos in str(fila).split(',')])))
        
        df = df.groupby(grupoCols).agg(aggDic).reset_index()

    df['VAEP/90'] = df['VAEP'] / df['Minutos Jugados'] * 90

    if verbose:
        df = df.sort_values('VAEP', ascending=False)
        seleccion = st.dataframe(df[['Nombre', 'Equipo', 'Posición Inicial', 'Minutos Jugados', 'VAEP', 'VAEP/90']], hide_index=True, on_select='rerun', selection_mode='single-row')
        return df.iloc[seleccion.selection.rows]

    return df


#Modificación de la función actions de Matplotsoccer
def actions_editada(
    location,
    action_type = None,
    result = None,
    team = None,
    label = None,
    labeltitle = None,
    color = 'white',
    ax = None,
    figsize = None,
    zoom = False,
    legloc = 'bottom',
    show = True,
    show_legend = True,
    markersize_factor = 1.0,   
    arrowsize_factor = 1.0,
):
    ax = mps.field(ax = ax, color = color, figsize = figsize, show = False)
    fig = plt.gcf()
    figsize, _ = fig.get_size_inches()
    arrowsize = math.sqrt(figsize) * arrowsize_factor

    # SANITIZING INPUT
    location = np.asarray(location)

    if action_type is None:
        m, n = location.shape
        action_type = ["pass" for i in range(m)]
        if label is None:
            show_legend = False
    action_type = np.asarray(action_type)

    if team is None:
        team = ["Team X" for t in action_type]
    team = np.asarray(team)
    assert team.ndim == 1
    if result is None:
        result = [1 for t in action_type]
    result = np.asarray(result)
    assert result.ndim == 1

    if label is None:
        label = [t for t in action_type]
    label = np.asarray(label)
    lines = get_lines_editada(label)

    if label is None:
        label = [[t] for t in action_type]
    label = np.asarray(label)
    if label.ndim == 1:
        label = label.reshape(-1, 1)
    assert label.ndim == 2
    indexa = np.asarray([list(range(1, len(label) + 1))]).reshape(-1, 1)
    label = np.concatenate([indexa, label], axis=1)
    if labeltitle is not None:
        labeltitle = list(labeltitle)
        labeltitle.insert(0, "")
        labeltitle = [labeltitle]
        label = np.concatenate([labeltitle, label])
        lines = get_lines_editada(label)
        titleline = lines[0]
        plt.plot(np.NaN, np.NaN, "-", color="none", label=titleline)
        plt.plot(np.NaN, np.NaN, "-", color="none", label="─" * len(titleline))
        lines = lines[1:]
    else:
        lines = get_lines_editada(label)

    m, n = location.shape
    if n != 2 and n != 4:
        raise ValueError("Location must have 2 or 4 columns")
    if n == 2:
        loc_end = location.copy()
        loc_end[:-1, :] = loc_end[1:, :]
        location = np.concatenate([location, loc_end], axis=1)
    assert location.shape[1] == 4

    text_offset = 3
    if zoom:
        x = np.concatenate([location[:, 0], location[:, 2]])
        y = np.concatenate([location[:, 1], location[:, 3]])
        xmin = min(x)
        xmax = max(x)
        ymin = min(y)
        ymax = max(y)
        mx = (xmin + xmax) / 2
        dx = (xmax - xmin) / 2
        my = (ymin + ymax) / 2
        dy = (ymax - ymin) / 2
        if type(zoom) == bool:
            d = max(dx, dy)
        else:
            d = zoom

        text_offset = 0.07 * d

        zoompad = 5

        xmin = max(mx - d, 0) - zoompad
        xmax = min(mx + d, spadl_config["length"]) + zoompad
        ax.set_xlim(xmin, xmax)
        ymin = max(my - d, 0) - zoompad
        ymax = min(my + d, spadl_config["width"]) + zoompad
        ax.set_ylim(ymin, ymax)

        h, w = fig.get_size_inches()
        h, w = xmax - xmin, ymax - ymin
        newh, neww = figsize, w / h * figsize

        fig.set_size_inches(newh, neww, forward=True)
        arrowsize = (w + h) / 2 / 105 * arrowsize

    eventmarkers = itertools.cycle(["s", "p", "h"])
    event_types = set(action_type)
    eventmarkerdict = {"pass": "o"}
    for eventtype in event_types:
        if eventtype != "pass":
            eventmarkerdict[eventtype] = next(eventmarkers)
    
    markersize = figsize * 2 * markersize_factor

    def get_color(type_name, te):
        home_team = team[0]
        if type_name == "dribble":
            return "black"
        elif te == home_team:
            return "blue"
        else:
            return "red"

    colors = np.array([get_color(ty, te) for ty, te in zip(action_type, team)])
    blue_n = np.sum(colors == "blue")
    red_n = np.sum(colors == "red")
    blue_markers = iter(list(cm.Blues(np.linspace(0.1, 0.8, blue_n))))
    red_markers = iter(list(cm.Reds(np.linspace(0.1, 0.8, red_n))))

    cnt = 1
    for ty, r, loc, color, line in zip(action_type, result, location, colors, lines):
        [sx, sy, ex, ey] = loc
        plt.text(sx + text_offset, sy, str(cnt))
        cnt += 1
        if color == "blue":
            c = next(blue_markers)
        elif color == "red":
            c = next(red_markers)
        else:
            c = "black"

        if ty == "dribble":
            ax.plot(
                [sx, ex],
                [sy, ey],
                color = c,
                linestyle = "--",
                linewidth = 2,
                label = line,
                zorder = zaction,
            )
        else:
            ec = "black" if r else "red"
            m = eventmarkerdict[ty]
            ax.plot(
                sx,
                sy,
                linestyle = "None",
                marker = m,
                markersize = markersize,
                label = line,
                color = c,
                mec = ec,
                zorder = zaction,
            )

            if abs(sx - ex) > 1 or abs(sy - ey) > 1:
                ax.arrow(
                    sx,
                    sy,
                    ex - sx,
                    ey - sy,
                    head_width = arrowsize,
                    head_length = arrowsize,
                    linewidth = 1,
                    fc = ec,
                    ec = ec,
                    length_includes_head = True,
                    zorder = zaction,
                )
    # leg = plt.legend(loc=9,prop={'family': 'monospace','size':12})
    if show_legend:
        if legloc == "top":
            leg = plt.legend(
                bbox_to_anchor = (0.5, 1.05),
                loc="lower center",
                prop={"family": "monospace"},
            )
        elif legloc == "right":
            leg = plt.legend(
                bbox_to_anchor = (1.05, 0.5),
                loc="center left",
                prop={"family": "monospace"},
            )
        else: 
            leg = plt.legend(
                bbox_to_anchor = (0.5, -0.05),
                loc="upper center",
                prop={"family": "monospace", 'size' : 13.5},
            )
    if show:
        plt.show()
    
#Modificación de la función get_lines de Matplotsoccer
def get_lines_editada(labels):
    labels = np.asarray(labels)
    if labels.ndim == 1:
        labels = labels.reshape(-1, 1)
    
    str_labels = [[str(cell) for cell in row] for row in labels]
    
    if not str_labels:
        return []
    
    max_widths = [
        max(len(row[col]) for row in str_labels) 
        for col in range(len(str_labels[0]))
    ]
    

    return [
        "  •  ".join(cell.ljust(max_widths[i]) for i, cell in enumerate(row))
        for row in str_labels
    ]


def muestra_pagina_visualizacion():
    st.title('Visualización de métricas VAEP')
    
    managers = []
    if 'manSB' not in st.session_state and 'manW' not in st.session_state:
        st.error('Para tener acceso a las métricas, vincula tus cuentas desde **Vinculación de cuentas**.')
        st.error('Si no dispones de cuentas de StatsBomb o Wyscout, accede directamente a **Gestión de Datos**.')
    else:
        if 'manSB' in st.session_state:
           managers.append(st.session_state.manSB)

        if 'manW' in st.session_state:
            managers.append(st.session_state.manW)

        listaCompetis = sorted(list(set(sum([man.lista_competiciones_descargadas() for man in managers], []))))

        col1, col2 = st.columns([1, 3])

        with col1:
            st.selectbox(
                label = 'Competición', 
                options = listaCompetis, 
                index = None, 
                placeholder = 'Elige una competición',
                key = 'visuCompeticion'
            )

        partidos = equipos = jugadores = pd.DataFrame()
        if st.session_state.get('visuCompeticion', None):
            if '/' in st.session_state.get('visuCompeticion'):
                for man in managers:
                    try:
                        st.session_state.eventos, partidos, equipos, jugadores = man.carga_datos_competicion(st.session_state.get('visuCompeticion')[:-10], st.session_state.get('visuCompeticion')[-9:])
                    except:
                        continue
            else:
                for man in managers:
                    try:
                        st.session_state.eventos, partidos, equipos, jugadores = man.carga_datos_competicion(st.session_state.get('visuCompeticion')[:-5], st.session_state.get('visuCompeticion')[-4:])

                    except:
                        continue

            
            #Nombres para mantener el funcionamiento del código para cuando se elige solo un partido
            equiposPartido = equipos['team_id'].tolist()
            equiposString = equipos['team_name'].tolist()

            if st.session_state.get('visuEquipo', None) and st.session_state.get('visuEquipo', None) not in equiposString:
                st.session_state.visuEquipo = None


        st.session_state.visuTorneo = False

        with col1:
            if not partidos.empty:
                if 'Final' in list(set(partidos['competition_stage'])):
                    st.session_state.visuTorneo = True
                    listaFases = sorted(list(set(partidos['competition_stage'])))
                else:
                    listaJornadas = sorted(list(set(partidos['game_day'])))
            else:
                listaFases = []
                listaJornadas = []

            if st.session_state.visuTorneo:
                if len(listaFases) == 1:
                    st.selectbox(
                        label = 'Fase', 
                        options = listaFases,
                        index = 0, 
                        disabled = (not st.session_state.get('visuCompeticion', None)), 
                        placeholder = 'Elige una fase',
                        key = 'visuFase'
                    )
                else:
                    st.selectbox(
                        label = 'Fase', 
                        options = listaFases,
                        index = None, 
                        disabled = (not st.session_state.get('visuCompeticion', None)), 
                        placeholder = 'Elige una fase',
                        key = 'visuFase'
                    )
                
                if st.session_state.get('visuFase', None):
                    equiposFase = equipos.loc[equipos['team_id'].isin(pd.concat([partidos.loc[partidos['competition_stage'] == st.session_state.get('visuFase', None)]['home_team_id'],
                                                partidos.loc[partidos['competition_stage'] == st.session_state.get('visuFase', None)]['away_team_id']]))]

                    equiposPartido = equiposFase['team_id'].tolist()
                    equiposString = equiposFase['team_name'].tolist()

                    listaJornadas = partidos.loc[partidos['competition_stage'] == st.session_state.visuFase]['game_day'].unique().tolist()

                    st.selectbox(
                        label = 'Jornada', 
                        options = listaJornadas,
                        index = (0 if len(listaJornadas) == 1 else None), 
                        disabled = (not st.session_state.get('visuFase', None)), 
                        placeholder = 'Elige una jornada',
                        key = 'visuJornada'
                    )

            else:

                st.selectbox(
                    label='Jornada', 
                    options=listaJornadas,
                    index = (0 if len(listaJornadas) == 1 else None), 
                    disabled=(not st.session_state.get('visuCompeticion', None)), 
                    placeholder='Elige una jornada',
                    key='visuJornada'
                )

        partidosSelec = pd.Series()
        if st.session_state.get('visuJornada', None):
            if st.session_state.visuTorneo:
                partidosSelec = partidos.loc[
                    (partidos['competition_stage'] == st.session_state.get('visuFase', None)) & 
                    (partidos['game_day'] == st.session_state.visuJornada)
                ]
            else:
                partidosSelec = partidos.loc[partidos['game_day'] == st.session_state.visuJornada]

            if st.session_state.get('visuEquipo', None):
                partidosSelec = partidosSelec.loc[(partidosSelec['home_team_id'] == equiposPartido[equiposString.index(st.session_state.visuEquipo)]) |
                                                  (partidosSelec['away_team_id'] == equiposPartido[equiposString.index(st.session_state.visuEquipo)])]
            
            partidosString = partidosSelec['result'].tolist()

        with col1:
            if partidosSelec.empty:
                partidosString = []

            st.selectbox(
                label = 'Partido', 
                options = partidosString,
                index = (0 if len(partidosString) == 1 else None), 
                disabled = (not st.session_state.get('visuCompeticion', None) or (not st.session_state.get('visuJornada', None) and not st.session_state.get('visuEquipo', None))), 
                placeholder = 'Elige un partido',
                key = 'visuPartido'
            )
            
        partidoSeleccionado = pd.DataFrame()
        if st.session_state.get('visuPartido', None):
            partidoSeleccionado = partidosSelec.iloc[partidosString.index(st.session_state.visuPartido)]
            idSelec = partidoSeleccionado['game_id']
            auxEquiposPartido = [
                equipos.loc[equipos['team_id'] == partidoSeleccionado['home_team_id']]['team_id'].iloc[0],
                equipos.loc[equipos['team_id'] == partidoSeleccionado['away_team_id']]['team_id'].iloc[0]
            ]
            if auxEquiposPartido != equiposPartido:
                equiposPartido = [
                    equipos.loc[equipos['team_id'] == partidoSeleccionado['home_team_id']]['team_id'].iloc[0],
                    equipos.loc[equipos['team_id'] == partidoSeleccionado['away_team_id']]['team_id'].iloc[0]
                ]
                equiposString = [equipos.loc[equipos['team_id'] == idEquipo]['team_name'].iloc[0] for idEquipo in equiposPartido]

        with col1:
            if not st.session_state.get('visuCompeticion', None) and partidoSeleccionado.empty:
                equiposString = []

            st.selectbox(
                label='Equipo', 
                options = equiposString,
                index=None, 
                disabled=(not st.session_state.get('visuPartido', None)) and (not st.session_state.get('visuCompeticion', None)), 
                placeholder='Elige un equipo',
                key='visuEquipo'
            )

        if st.session_state.get('visuCompeticion', None):
            st.session_state.eventosFiltrados = filtra_eventos(st.session_state.get('eventos', None), 
                                                              st.session_state.get('visuFase', None),
                                                              st.session_state.get('visuJornada', None),
                                                              st.session_state.get('visuPartido', None),
                                                              st.session_state.get('visuEquipo', None)
                                                            )


        with col1:
            if st.session_state.get('visuCompeticion', None) and st.session_state.get('eventosFiltrados', None) is not None and not st.session_state.get('eventosFiltrados', None).empty:
                listaTipos = st.session_state.get('eventosFiltrados', None)['type_name'].unique().tolist()
            else:
                listaTipos = []
            st.selectbox(
                label = 'Tipo de acción',
                options = listaTipos,
                index = (0 if len(listaTipos) == 1 else None),
                disabled = (not st.session_state.get('visuCompeticion', None) and not listaTipos),
                placeholder = 'Elige un tipo de acción',
                key = 'visuTipo'
            )


        with col2:
            st.markdown("<h3 style='text-align: center'>Ranking de jugadores por VAEP</h3>", unsafe_allow_html=True)

            if st.session_state.get('visuCompeticion', None):
                if st.session_state.get('visuTipo', None):
                    st.session_state.eleccion = calcula_vaep(st.session_state.get('eventosFiltrados', None)[st.session_state.get('eventosFiltrados', None)['type_name'] == st.session_state.get('visuTipo', None)], jugadores, verbose = True)
                
                else:
                    st.session_state.eleccion = calcula_vaep(st.session_state.get('eventosFiltrados', None), jugadores, verbose = True)

            else:
                st.info('ℹ️ Para obtener el ranking, selecciona una competición.')

    st.write('')
    st.markdown("<h3 style='text-align: center'>Visualizador de jugadas</h3>", unsafe_allow_html=True)

    if st.session_state.get('eleccion', None) is not None and not st.session_state.get('eleccion', None).empty and st.session_state.get('visuPartido', None):
        evs = st.session_state.get('eventosFiltrados', None)
        if st.session_state.get('visuTipo', None):
            eventosJugador = evs[(evs['player_name'] == st.session_state.eleccion['Nombre'].iloc[0]) & (evs['type_name'] == st.session_state.visuTipo)].sort_values(['game_id', 'period_id', 'time_seconds'], ascending = True)
        else:
            eventosJugador = evs[evs['player_name'] == st.session_state.eleccion['Nombre'].iloc[0]].sort_values(['game_id', 'period_id', 'time_seconds'], ascending = True)
        # mps.actions(eventosJugador[['start_x', 'start_y', 'end_x', 'end_y']], show = False, )
        # st.pyplot(plt.gcf())
        def formatea_evento(fila):
            resultado = 'exitoso' if fila['result_name'] == 'success' else 'no exitoso'
            return f'{formatea_tiempo(fila)}, {fila['type_name']} {resultado}'
        
        def formatea_tiempo(fila):
            tiempoTotal = fila['time_seconds']
            if fila['period_id'] == 2:
                tiempoTotal = tiempoTotal + 45 * 60

            elif fila['period_id'] == 3:
                tiempoTotal = tiempoTotal + 90 * 60

            elif fila['period_id'] == 4:
                tiempoTotal = tiempoTotal + 105 * 60

            elif fila['period_id'] == 5:
                return 'Tanda de penaltis'
            
            minutos = int(tiempoTotal // 60)
            segundos = tiempoTotal % 60
            return f'{minutos:02d}:{segundos:05.2f}'
        
        
        colu1, colu2, colu3 = st.columns(3)

        listaEventosJugador = eventosJugador.apply(formatea_evento, axis=1).tolist()

        with colu1:
            st.selectbox(label = 'Elige una acción', options = listaEventosJugador, index = 0, key = 'accionVisu')

        with colu2:
            minElegido = st.slider(label = 'Número de acciones previas', min_value = 0, max_value = 20, value = 0)

        with colu3:
            maxElegido = st.slider(label = 'Número de acciones posteriores', min_value = 0, max_value = 20, value = 0)

        accionElegida = eventosJugador.iloc[listaEventosJugador.index(st.session_state.accionVisu)]
        eventosPartidoAccion = st.session_state.get('eventos', None)[st.session_state.get('eventos', None)['game_id'] == accionElegida['game_id']]

        # Resetea el índice para que coincida con las posiciones
        eventosPartidoAccion = eventosPartidoAccion.reset_index(drop=True)

        condicion = eventosPartidoAccion['time_seconds'] == accionElegida['time_seconds']
        posicion = eventosPartidoAccion[condicion].index[0]  # Ahora sí es la posición correcta

        accionesRepresentar = eventosPartidoAccion.iloc[max(0, posicion - minElegido): min(len(eventosPartidoAccion), posicion + maxElegido + 1)]
        accionesRepresentar['time_seconds'] = accionesRepresentar.apply(formatea_tiempo, axis = 1)
        accionesRepresentar['vaep_value'] = accionesRepresentar['vaep_value'].apply(lambda x: 0.0 if round(x, 3) == 0 else round(x, 3)).apply(lambda x: f'{x:.3f}')
        
        plt.figure(figsize=(12, 8))
        actions_editada(accionesRepresentar[['start_x', 'start_y', 'end_x', 'end_y']], 
                        action_type = accionesRepresentar['type_name'],
                        team = accionesRepresentar['team_name'],
                        result = accionesRepresentar['result_name'],
                        label = accionesRepresentar[['time_seconds', 'type_name', 'result_name',  'vaep_value', 'player_name', 'team_name']],
                        labeltitle = ['Tiempo', 'Tipo de acción', 'Resultado', 'VAEP', 'Jugador', 'Equipo'],
                        show = False, 
                        color = 'green',
                        figsize = 14.5,
                        markersize_factor = 0.5, 
                        arrowsize_factor = 0.5)
        
        fig = plt.gcf()
        fig.patch.set_facecolor('none')
        st.pyplot(fig)

    else:
        st.info('ℹ️ Para visualizar jugadas, elige un partido y un jugador.')
