from nicegui import ui

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        with ui.row().classes('items-center justify-between mb-4'):
            ui.label('API Key 列表').classes('text-slate-800 text-xl text-bold')
            ui.button('新增API Key', on_click=lambda: ui.open('logout'), icon='add', color='blue-400').props('flat').classes('text-white shadow-md shadow-blue-200')

        with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl'):
            columns = [
                {'name': 'service', 'label': '服務', 'field': 'service', 'align': 'left'},
                {'name': 'api_key', 'label': 'API Key', 'field': 'api_key', 'sortable': False, 'align': 'left'},
                {'name': 'expiring_at', 'label': '有效期', 'field': 'expiring_at', 'sortable': True, 'align': 'left'},
                {'name': 'status', 'label': '狀態', 'field': 'status', 'sortable': True, 'align': 'left'},
            ]
            rows = [
                {'service': 'test 持證自拍驗證', 'api_key': 'mlknqerAls12asdf_1fsq', 'expiring_at': '2024/01/08 14:30', 'status': '生效中'},
                {'service': 'testPs P圖偵測', 'api_key': 'apower;lw112asdf_1fsq', 'expiring_at': '2024/01/08 14:30', 'status': '生效中'},
            ]
            ui.table(columns=columns, rows=rows, row_key='name').classes('w-full')