"""Optional browser smoke check: python tests/browser_group_campaigns.py.

Uses an isolated temporary database; never connects to Telegram.
Requires Playwright and its Chromium browser in the development environment.
"""
import re
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flask import Flask, render_template, session
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server, WSGIRequestHandler
from group_campaigns import register_campaign_routes


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def run():
    with tempfile.TemporaryDirectory() as directory:
        app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
        app.secret_key = 'browser-test-only'

        class Sessions:
            def load_sessions(self, **kwargs):
                return [{'session_name': 'test.session', 'first_name': 'Sessão', 'last_name': 'de teste', 'phone': '+5500000000000', 'active': True}]

        register_campaign_routes(app, lambda function: function,
                                 lambda username: {'data_dir': directory}, lambda username: Sessions(),
                                 lambda: (None, None), lambda *args, **kwargs: (False, 'Test mode'),
                                 lambda *args, **kwargs: None, lambda username: {})

        @app.route('/api/sessions')
        def sessions():
            return {'sessions': Sessions().load_sessions()}

        @app.route('/')
        def page():
            session['username'] = 'test'
            styles = '\n'.join(re.findall(r'<style[^>]*>.*?</style>', (ROOT / 'templates/index.html').read_text(encoding='utf-8'), re.S))
            return ('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/static/style.css">'
                    + styles + '</head><body data-theme="light"><a href="#" class="menu-item" data-tab="comingSoon">Tarefas de grupos</a><main class="main-content">'
                    + render_template('group_campaigns.html') + '</main><script>function showNotification(){};'
                    'document.getElementById("comingSoon").classList.add("active");</script>'
                    '<script src="/static/group_campaigns.js"></script></body></html>')

        server = make_server('127.0.0.1', 0, app, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.locator('[data-tab="comingSoon"]').click()
                page.locator('#campaign-sessions option').wait_for(state='attached')
                assert page.locator('.gc-session-identity strong').inner_text() == 'Sessão de teste'
                assert page.locator('.gc-session-identity small').inner_text() == '+5500000000000'
                page.locator('#campaign-name').fill('Tarefa de teste')
                page.locator('#campaign-session-options input[value="test.session"]').check()
                page.locator('#campaign-warming').select_option('yes')
                page.locator('#campaign-phrases-file').set_input_files({'name': 'frases.txt', 'mimeType': 'text/plain', 'buffer': 'Olá\nBem-vindo'.encode()})
                page.wait_for_function('document.getElementById("campaign-phrases").value.includes("Bem-vindo")')
                page.locator('#campaign-create-form button').click()
                page.locator('#campaign-list .gc-task').wait_for()
                assert page.locator('#campaign-list details[data-detail^="group-"]').count() == 10
                page.locator('#campaign-bank > summary').click()
                page.locator('#campaign-leads-file').set_input_files({'name': 'leads.json', 'mimeType': 'application/json', 'buffer': b'{"members":[{"id":123,"username":"lead_test"}]} '})
                page.locator('#campaign-leads-form button').click()
                page.wait_for_function('document.getElementById("campaign-lead-total").textContent === "1"')
                page.locator('details[data-detail="group-1"] > summary').click()
                group = page.locator('form[data-group="1"]')
                group.locator('[name="daily_limit"]').fill('12')
                group.locator('button[value="limit"]').click()
                page.wait_for_function('document.querySelector("details[data-detail=group-1] summary").textContent.includes("/12")')
                group.locator('.gc-replace > summary').click()
                group.locator('[name="title"]').fill('Grupo substituto')
                group.locator('button[value="replace"]').click()
                page.wait_for_function('document.getElementById("campaign-list").textContent.includes("Grupo substituto")')
                assert page.locator('#campaign-list details[data-detail^="group-"]').count() == 10
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('#campaign-new').click()
                assert page.locator('#campaign-create-form button').is_visible()
                page.wait_for_function('document.documentElement.scrollWidth <= window.innerWidth')
                import os
                if os.environ.get('CAMPAIGN_SCREENSHOT_DIR'):
                    output = Path(os.environ['CAMPAIGN_SCREENSHOT_DIR'])
                    page.screenshot(path=str(output / 'campaign-mobile.png'), full_page=True)
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    page.screenshot(path=str(output / 'campaign-desktop.png'), full_page=True)
                    page.evaluate('document.body.dataset.theme = "dark"')
                    page.screenshot(path=str(output / 'campaign-dark.png'), full_page=True)
                assert not errors, errors
                browser.close()
                print('Browser smoke passed: create 10 groups, phrase upload, import leads, edit limit, replace group, mobile viewport.')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    run()
