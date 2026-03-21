from nicegui import ui

@ui.page('/')
def index():
    ui.label('Mermaid Test')
    code = """
graph TD
    A --> B
    B --> C
    C --> A
"""
    with ui.card():
        ui.mermaid(code)
    
    ui.label('Multi-line text below')

ui.run(port=8081)
