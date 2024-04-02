from nicegui import ui

def generate():
    ui.query('body').classes('bg-slate-100')
    with ui.element('div').classes('m-0 p-4 bg-slate-100 w-full'):
        ui.label('驗證紀錄').classes('text-slate-800 text-xl text-bold mb-4')
        with ui.card().classes('w-full shadow-2xl shadow-slate-200 rounded-xl'):
            columns = [
                {'name': 'task_id', 'label': '驗證編號', 'field': 'task_id', 'align': 'left'},
                {'name': 'datetime', 'label': '驗證日期', 'field': 'datetime', 'align': 'left'},
                {'name': 'taiwanese_id_no', 'label': '身分證字號', 'field': 'taiwanese_id_no', 'sortable': False, 'align': 'left'},
                {'name': 'name', 'label': '姓名', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'result', 'label': '驗證結果', 'field': 'result', 'sortable': True, 'align': 'left'},
            ]
            rows = [
                {'task_id': 'JFOQWERL1KAQ', 'datetime': '10月30日', 'taiwanese_id_no': 'A123456789', 'name': '陳大明', 'result': '通過'},
                {'task_id': 'LKOPWJQ2MFLQ', 'datetime': '10月25日', 'taiwanese_id_no': 'F220099333', 'name': '李小美', 'result': '失敗'},
            ]
            with ui.dialog() as dialog, ui.card().classes('p-8'):
                with ui.grid(columns=2).classes('w-full'):
                    ui.label('驗證編號：JFOQWERL1KAQ').classes('text-left')
                    ui.label('驗證日期：2023年12月1日').classes('text-right')

                ui.label('驗證通過').classes('text-3xl text-green-700 text-bold')
                ui.separator()        
                with ui.grid(columns=2):
                    with ui.column():
                        ui.label('身分證正面').classes('text-lg text-blue-500 text-bold')
                        with ui.grid(columns=2):
                            ui.label('身分證字號').classes('text-bold')
                            ui.label('A123456789')
                            ui.label('姓名').classes('text-bold')
                            ui.label('陳大明')
                            ui.label('生日').classes('text-bold')
                            ui.label('087年7月8日')
                            ui.label('發證日期').classes('text-bold')
                            ui.label('102年3月27日')
                    with ui.column():
                        ui.image('https://www.ris.gov.tw/documents/data/apply-idCard/images/ddccc3f2-2aa9-4e92-9578-41d035af66ea.jpg')

                    with ui.column():
                        ui.label('身分證反面').classes('text-lg text-blue-500 text-bold mt-8')
                        with ui.grid(columns=2):
                            ui.label('父親姓名').classes('text-bold')
                            ui.label('陳小明')
                            ui.label('母親姓名').classes('text-bold')
                            ui.label('王惟')
                            ui.label('配偶姓名').classes('text-bold')
                            ui.label('林飛凡')
                            ui.label('兵役狀況').classes('text-bold')
                            ui.label('免役')
                            ui.label('出生地').classes('text-bold')
                            ui.label('臺灣省彰化縣')
                            ui.label('戶籍地').classes('text-bold')
                            ui.label('台北市大安區松青路2號')
                            ui.label('序號').classes('text-bold')
                            ui.label('098341829342')
                    with ui.column():
                        ui.image('https://www.ris.gov.tw/documents/data/apply-idCard/images/4f3bafb8-502b-400f-ab63-a819044e2621.jpg').classes('mt-8')

                    with ui.column(): 
                        ui.label('健保卡').classes('text-lg text-blue-500 text-bold mt-8')
                        with ui.grid(columns=2):
                            ui.label('身分證字號').classes('text-bold')
                            ui.label('A123456789')
                            ui.label('姓名').classes('text-bold')
                            ui.label('陳大明')
                            ui.label('生日').classes('text-bold')
                            ui.label('087年7月8日')
                            ui.label('卡號').classes('text-bold')
                            ui.label('000012983402')
                    with ui.column():
                        ui.image('https://pro.6000.gov.tw/inc/img/global/qa-all-1.png').classes('mt-8')

                ui.button('關閉', on_click=dialog.close).classes('self-center')

            ui.table(columns=columns, rows=rows, row_key='name').on('rowClick', lambda x: dialog.open()).classes('w-full')

