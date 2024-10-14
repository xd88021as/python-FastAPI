from nicegui import ui

def login():
    ui.open('/')

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.card().classes('absolute-center shadow-2xl shadow-slate-200 rounded-xl p-8 items-center w-1/4'):
        ui.label('歡迎回來').classes('text-slate-800 text-xl text-bold')
        ui.label('test').classes('text-slate-800 text-3xl text-bold')
        username = ui.input('Email').props('outlined stack-label').on('keydown.enter', login).classes('w-full my-2')
        password = ui.input('密碼', password=True, password_toggle_button=True).props('outlined stack-label').on('keydown.enter', login).classes('w-full my-2')
        ui.button('登入', on_click=login).classes('w-full py-3 my-2')
        ui.link('忘記密碼', 'https://github.com/zauberzeug/nicegui')