"""Isolated browser checks; uses sample sessions and never contacts Telegram."""
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flask import Flask, render_template
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def run():
    app = Flask(__name__, static_folder=str(ROOT / 'static'), template_folder=str(ROOT / 'templates'))
    template = (ROOT / 'templates/index.html').read_text(encoding='utf-8')
    extraction = template.split('<!-- Tab: Extrair -->')[1].split('<!-- Tab:', 1)[0]
    styles = '\n'.join(re.findall(r'<style[^>]*>.*?</style>', template, re.S))
    busy = {'value': True}

    @app.route('/api/group-visibility/sessions')
    def sessions():
        return {'success': True, 'sessions': [
            {'session_name': 'free.session', 'available': True},
            {'session_name': 'task.session', 'available': not busy['value'], 'unavailable_reason': 'Reservada por tarefa de adição' if busy['value'] else ''}]}

    @app.route('/api/group-visibility')
    def status():
        return {'success': True, 'job': None}

    @app.route('/')
    def page():
        links = ''.join(f'<link rel="stylesheet" href="/static/{name}.css">' for name in
                        ['style', 'studio', 'refined', 'workspace', 'dark', 'motion-plans', 'spatial', 'group_visibility', 'extraction'])
        return ('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
                + styles + links + '<link rel="stylesheet" href="/static/ui/interface.css"></head><body data-design="studio"><a href="#groupVisibility" data-tab="groupVisibility">Membros visíveis</a>'
                '<main style="padding:24px;max-width:1200px;margin:auto">' + extraction + render_template('group_visibility.html')
                + '</main><script src="/static/group_visibility.js"></script></body></html>')

    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1100})
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.locator('#extract').evaluate("element => element.classList.add('active')")
            page.locator('#extract-session').evaluate("element => element.innerHTML='<option value=0>free.session</option>'")
            page.locator('#extract-session-list').evaluate("element => element.innerHTML='<div class="
                "\"service-session-option selected\"><input type=radio checked><div><strong>Sessão de exemplo</strong>"
                "<small>@exemplo</small></div><span class=service-session-status>Livre</span></div>'")
            source = (ROOT / 'static/script.js').read_text(encoding='utf-8')
            handler = source.split('function extractMembersList()')[1].split('// Download exportação')[0]
            page.add_script_tag(content='window.sent=null;const socket={emit:(name,payload)=>window.sent=payload};function showNotification(){};function extractMembersList()' + handler)
            page.locator('#extract-group-list').fill('\n'.join(f'https://t.me/group_{index}' for index in range(125)))
            page.locator('[onclick="extractMembersList()"]').click()
            assert page.evaluate('window.sent.group_links.length') == 125
            page.screenshot(path=str(ROOT / '.runtime/extraction-desktop.png'), full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.locator('#extract').evaluate('element => element.scrollWidth <= element.clientWidth')
            page.screenshot(path=str(ROOT / '.runtime/extraction-mobile.png'), full_page=True)
            page.locator('#extract').evaluate("element => element.classList.remove('active')")
            page.locator('#groupVisibility').evaluate("element => element.classList.add('active')")
            page.locator('[data-tab="groupVisibility"]').click()
            page.locator('#gv-sessions input[value="task.session"]').wait_for()
            assert page.locator('#gv-sessions input[value="task.session"]').is_disabled()
            assert page.locator('#gv-sessions input[value="free.session"]').is_enabled()
            assert 'Reservada por tarefa' in page.locator('#gv-sessions').text_content()
            page.screenshot(path=str(ROOT / '.runtime/visibility-sessions-mobile.png'), full_page=True)
            busy['value'] = False
            page.locator('#gv-reload').click()
            page.wait_for_function("!document.querySelector('#gv-sessions input[value=\"task.session\"]').disabled")
            browser.close()
    finally:
        server.shutdown()
    print('Browser checks passed: 125 links, desktop/mobile layout, busy sessions and refresh.')


if __name__ == '__main__':
    run()
