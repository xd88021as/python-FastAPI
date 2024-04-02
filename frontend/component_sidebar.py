from nicegui import ui
import numpy as np
from matplotlib import pyplot as plt

SIDEBAR_BUTTON_PROPS = 'flat color=slate-600 align=left'
SIDEBAR_BUTTON_SELECTED_PROPS = 'flat color=blue-400 align=left'
SIDEBAR_BUTTON_CLASSES = 'w-full py-4'
SIDEBAR_BUTTON_STYLE = 'margin-top: -7px; margin-bottom: -7px'
SIDEBAR_ITEMS = [
    {'title': '總覽', 'icon': 'dashboard', 'name': 'pix'},
    {'title': '驗證紀錄', 'icon': 'history', 'name': 'history'},
    {'title': '帳號資料維護', 'icon': 'person', 'name': 'person'},
    {'title': 'API KEY', 'icon': 'key', 'name': 'key'},
    {'title': 'Demo', 'icon': 'science', 'name': 'static/demo.html'},
    {'title': '開發者文件', 'icon': 'description', 'name': 'description'}
]

def generate(current):
    with ui.left_drawer(top_corner=False, bottom_corner=True, elevated=False).classes('bg-white shadow-lg shadow-slate-200 py-10'):
        [ui.button(item['title'], on_click=lambda item=item: ui.open(item['name']), icon=item['icon'], color='white')
            .props(SIDEBAR_BUTTON_SELECTED_PROPS if current == item['name'] else SIDEBAR_BUTTON_PROPS)
            .classes(SIDEBAR_BUTTON_CLASSES)
            .style(SIDEBAR_BUTTON_STYLE) for item in SIDEBAR_ITEMS]
