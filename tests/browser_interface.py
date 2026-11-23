"""Full-template motion checks with fake APIs; never contacts Telegram or real accounts."""
import json
import sys
import threading
from pathlib import Path

from flask import Flask, render_template
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]


class Quiet(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def run():
    app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
    app.secret_key = 'isolated-browser-test'

    @app.route('/')
    def marketing():
        return render_template('login.html')

    @app.route('/workspace')
    def workspace():
        return render_template('index.html', username='Teste visual', app_version='test', app_commit='motion')

    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    artifacts = ROOT / '.runtime' / 'interface'
    artifacts.mkdir(parents=True, exist_ok=True)
    observations = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height in [(1440, 900), (390, 844)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=width < 680, has_touch=width < 680)
                # Keep sockets and external web assets out of the isolated test.
                context.add_init_script('window.io = () => ({on(){},emit(){}});')
                def route_request(route):
                    url = route.request.url
                    if '/api/' in url:
                        if '/events/stream' in url:
                            route.fulfill(status=200, content_type='text/event-stream', body='data: []\n\n')
                        else:
                            route.fulfill(json={'success': True, 'sessions': [], 'tasks': [], 'campaigns': [], 'clones': [], 'processes': [], 'groups': [], 'batches': [], 'history': [], 'items': [], 'locks': {}, 'stats': {}, 'counts': {}, 'config': {}, 'settings': {}, 'data': [], 'total': 0})
                    elif '127.0.0.1' in url:
                        route.continue_()
                    elif 'socket.io' in url:
                        route.fulfill(body='/* socket stub supplied before page scripts */', content_type='application/javascript')
                    else:
                        route.abort()
                context.route('**/*', route_request)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                base = f'http://127.0.0.1:{server.server_port}'
                page.goto(base, wait_until='domcontentloaded')
                page.wait_for_function('window.TGInterface?.smoothScroll === true')
                page.locator('#hero-title .shiny-text').wait_for()
                assert page.locator('#hero-title').inner_text().replace('\n', ' ').strip() == 'Automação para seu Telegram.'
                page.mouse.wheel(0, 600)
                page.wait_for_function('window.scrollY > 200')
                page.locator('a[href="#acesso"]').first.click()
                page.wait_for_function('location.hash === "#acesso" && document.activeElement.id === "acesso"',timeout=3000)
                page.locator('#loginTab').click()
                page.locator('#registerTab').focus()
                page.keyboard.press('Enter')
                assert page.locator('#registerTab').get_attribute('aria-selected') == 'true'
                page.screenshot(path=str(artifacts / f'marketing-{width}.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.goto(base + '/workspace', wait_until='domcontentloaded')
                page.wait_for_function('window.TGInterface?.smoothScroll === true')
                page.locator('.dashboard-welcome .shiny-text').wait_for()
                tabs = page.locator('.menu-item[data-tab]').evaluate_all('(nodes) => [...new Set(nodes.map(n => n.dataset.tab))]')
                visited = []
                for tab in tabs:
                    # Use the real navigation handler, including tabs inside the mobile drawer.
                    page.locator(f'.menu-item[data-tab="{tab}"]').first.evaluate('(node) => node.click()')
                    page.wait_for_function('(id) => document.getElementById(id)?.classList.contains("active")', arg=tab)
                    page.wait_for_timeout(420)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), tab
                    visited.append(tab)
                page.locator('.menu-item[data-tab="comingSoon"]').first.evaluate('(node) => node.click()')
                page.locator('#campaign-new').click()
                page.locator('#campaign-name').fill('Formulário preservado')
                assert page.locator('#campaign-name').input_value() == 'Formulário preservado'
                if width > 680:
                    names = page.locator('#campaign-names')
                    names.fill('\n'.join(f'Grupo {index}' for index in range(80)))
                    names.scroll_into_view_if_needed()
                    page.wait_for_timeout(800)
                    names.evaluate('(node) => {node.scrollTop = 0;}')
                    box = names.bounding_box()
                    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    before_scroll = page.evaluate('scrollY')
                    page.mouse.wheel(0, 180)
                    page.wait_for_timeout(250)
                    assert names.evaluate('(node) => node.scrollTop') > 0
                    assert abs(page.evaluate('scrollY') - before_scroll) < 3
                    names.fill('')
                page.screenshot(path=str(artifacts / f'workspace-{width}.png'), full_page=True)
                # Runtime preference changes must fully restore native scrolling and text.
                page.emulate_media(reduced_motion='reduce')
                page.wait_for_function('window.TGInterface?.smoothScroll === false')
                assert page.locator('.ui-shiny-host,.ui-spotlight-layer').count() == 0
                assert page.locator('#campaign-name').input_value() == 'Formulário preservado'
                # On a fresh navigation the reduced-motion path starts natively too.
                page.goto(base, wait_until='domcontentloaded')
                page.wait_for_function('window.TGInterface?.smoothScroll === false')
                assert page.locator('#hero-title').is_visible()
                assert page.locator('.ui-shiny-host,.ui-spotlight-layer').count() == 0
                page.emulate_media(reduced_motion='no-preference')
                page.wait_for_function('window.TGInterface?.smoothScroll === true')
                assert not errors, errors
                observations.append({'viewport': f'{width}x{height}', 'tabs': visited, 'errors': errors})
                context.close()
            browser.close()
        (artifacts / 'checks.json').write_text(json.dumps(observations, indent=2), encoding='utf-8')
        print('Interface browser checks passed:', observations)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    run()
