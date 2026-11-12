/* Shared accessibility and URL navigation; no data or Telegram operations. */
(() => {
    'use strict';
    document.querySelectorAll('i.fas,i.far,i.fab').forEach(icon => icon.setAttribute('aria-hidden', 'true'));
    if (!document.documentElement.hasAttribute('data-workspace')) return;
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.mobile-toggle');
    const links = [...document.querySelectorAll('.menu-item[data-tab]')];
    const main = document.getElementById('workspace-main');
    const overlay = document.querySelector('.sidebar-overlay');

    function syncDrawer() {
        const open = sidebar.classList.contains('open');
        sidebar.inert = innerWidth <= 800 ? !open : document.body.classList.contains('sidebar-collapsed');
        toggle.setAttribute('aria-expanded', String(open));
    }
    new MutationObserver(syncDrawer).observe(sidebar, {attributes: true, attributeFilter: ['class']});
    new MutationObserver(syncDrawer).observe(document.body, {attributes: true, attributeFilter: ['class']});

    function closeMenu(returnFocus) {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
        toggle.setAttribute('aria-expanded', 'false');
        syncDrawer();
        if (returnFocus) toggle.focus();
    }
    function syncNavigation() {
        links.forEach(link => {
            const active = link.classList.contains('active');
            if (active) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
    }
    function activateHash() {
        const id = location.hash.slice(1);
        const link = links.find(item => item.dataset.tab === id);
        if (link && !link.classList.contains('active')) link.click();
    }
    links.forEach(link => link.addEventListener('click', event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        history.replaceState(null, '', '#' + link.dataset.tab);
        syncNavigation();
        window.scrollTo({top: 0, behavior: 'instant'});
        if (innerWidth <= 800) {
            closeMenu(false);
            main.focus({preventScroll: true});
        }
    }));
    toggle.addEventListener('click', () => {
        syncDrawer();
        if (sidebar.classList.contains('open')) links.find(link => link.classList.contains('active'))?.focus();
    });
    document.addEventListener('keydown', event => {
        if (innerWidth > 800 || !sidebar.classList.contains('open')) return;
        if (event.key === 'Escape') { event.preventDefault(); closeMenu(true); }
        if (event.key === 'Tab') {
            const controls = [...sidebar.querySelectorAll('a[href],button:not(:disabled)')].filter(el => el.getClientRects().length);
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && (document.activeElement === first || !sidebar.contains(document.activeElement))) {event.preventDefault();last?.focus();}
            else if (!event.shiftKey && (document.activeElement === last || !sidebar.contains(document.activeElement))) {event.preventDefault();first?.focus();}
        }
    });
    window.addEventListener('hashchange', activateHash);
    window.addEventListener('resize', () => {if (innerWidth > 800) closeMenu(false);syncDrawer();});
    document.querySelectorAll('button:not([aria-label])').forEach(button => {
        if (!button.textContent.trim() && button.title) button.setAttribute('aria-label', button.title);
    });
    document.querySelectorAll('input,select,textarea').forEach(control => {
        if (!control.name && control.id) control.name = control.id;
    });
    syncNavigation();
    syncDrawer();
    activateHash();
})();
