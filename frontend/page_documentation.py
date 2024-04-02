from nicegui import ui

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        with ui.element('div').classes('w-full shadow-2xl shadow-slate-200 rounded-xl bg-white'):
            ui.html('<iframe src="/docs" style="width:100%;height:800px;"></iframe>')