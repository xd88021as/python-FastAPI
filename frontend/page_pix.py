from nicegui import ui
import numpy as np
from matplotlib import pyplot as plt

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        ui.label('儀表版').classes('text-slate-800 text-xl text-bold mb-4')

        with ui.grid(columns=2):
            with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl p-6'):
                ui.label('點數剩餘').classes('text-slate-400')
                ui.label('250,000').classes('text-4xl text-bold').style('margin-top: -15px')


            with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl p-6'):
                ui.label('今天使用次數').classes('text-slate-400')
                ui.label('9,120').classes('text-4xl text-bold').style('margin-top: -15px')

            with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl p-6'):
                chart = ui.highchart({
                    'title': False,
                    'chart': {'type': 'bar'},
                    'xAxis': {'categories': ['A', 'B']},
                    'series': [
                        {'name': 'Alpha', 'data': [0.1, 0.2]},
                        {'name': 'Beta', 'data': [0.3, 0.4]},
                    ],
                }).classes('w-full h-64')


            with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl p-6'):
                chart = ui.highchart({
                    'title': False,
                    'chart': {'type': 'pie'},
                    'series': [{
                        'name': '總數',
                        'colorByPoint': True,
                        'data': [{
                            'name': '通過',
                            'y': 74.77,
                            'sliced': True,
                            'selected': True
                        },  {
                            'name': '不通過',
                            'y': 12.82
                        }],
                    }],
                }).classes('w-full h-64')
