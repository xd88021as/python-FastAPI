from nicegui import ui
import numpy as np
from matplotlib import pyplot as plt

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        ui.label('Demo Page Coming Soon').classes('text-slate-800 text-xl text-bold mb-4')

