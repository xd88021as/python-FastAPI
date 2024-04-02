from nicegui import ui

def on_click_save():
    print ('on click save button')

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        ui.label('帳號資料維護').classes('text-slate-800 text-xl text-bold mb-4')
        with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl p-8'):
            ui.input(
                label='公司名稱',
                placeholder='例：普匯金融股份有限公司',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.input(
                label='統一編號',
                placeholder='例：68566881',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.input(
                label='統一編號',
                placeholder='例：68566881',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.input(
                label='聯絡人',
                placeholder='例：陳小明',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.input(
                label='聯絡人Email',
                placeholder='例：peterChen@gmail.com',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.input(
                label='聯絡人手機',
                placeholder='例：0912345678',
                on_change=lambda e: result.set_text('you typed: ' + e.value),
                validation={'Input too long': lambda value: len(value) < 20}
            ).props('outlined stack-label').classes('w-full')
            ui.select(
                label='額度低於多少發送低額度通知？',
                options=['100點', '500點', '1000點'],
                value='500點'
            ).props('outlined stack-label').classes('w-full')
            result = ui.label()
            ui.button('儲存f', on_click=lambda: on_click_save(), icon='save', color='blue-400').props('flat').classes('self-end text-white shadow-md shadow-blue-200')
