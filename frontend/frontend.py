from nicegui import ui
from fastapi import FastAPI
import component_sidebar
import component_header
import page_account
import page_demo
import page_documentation
import page_history
import page_key
import page_login
import page_pix

def init(fastapi_app: FastAPI) -> None:
    @ui.page('/login')
    def login() -> None:
        page_login.generate()

    @ui.page('/logout')
    def logout() -> None:
        ui.label('你已登出')

    @ui.page('/history')
    def history() -> None:
        component_header.generate()
        component_sidebar.generate('history')
        page_history.generate()

    @ui.page('/person')
    def person() -> None:
        component_header.generate()
        component_sidebar.generate('person')
        page_account.generate()

    @ui.page('/key')
    def key() -> None:
        component_header.generate()
        component_sidebar.generate('key')
        page_key.generate()

    @ui.page('/demo')
    def demo() -> None:
        component_header.generate()
        component_sidebar.generate('demo')
        page_demo.generate()

    @ui.page('/description')
    def desciprtion() -> None:
        component_header.generate()
        component_sidebar.generate('description')
        page_documentation.generate()

    @ui.page('/')
    @ui.page('/pix')
    def home() -> None:
        component_header.generate()
        component_sidebar.generate('pix')
        page_pix.generate()

    ui.run_with(fastapi_app)