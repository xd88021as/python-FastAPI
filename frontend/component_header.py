from nicegui import ui

HEADER_CLASSES = 'items-center justify-between bg-white shadow-lg shadow-slate-200'
BRAND_NAME_CLASSES = 'text-slate-800 text-2xl text-bold pl-4'

def generate():
    with ui.header(elevated=False).classes(HEADER_CLASSES):
        ui.label('test').classes(BRAND_NAME_CLASSES)
        with ui.button('陳小明', on_click=lambda: right_drawer.toggle(), icon='person', color='slate-400').props('flat color=white').classes('shadow-md shadow-slate-200'):
            with ui.menu().classes('shadow-lg shadow-slate-200') as menu:
                ui.menu_item('聯絡客服', lambda: result.set_text('Selected item 1'))
                ui.menu_item('登出', lambda: ui.open('/login'))
