import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import ShinyText from './reactbits/ShinyText.jsx';
import SpotlightCard from './reactbits/SpotlightCard.jsx';
import { createEnergyField } from './energy.js';
import './interface.css';

// Presentation only. No account, task, authentication or API state is owned here.
gsap.registerPlugin(ScrollTrigger);
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const fine = matchMedia('(hover: hover) and (pointer: fine)');
const headingSelector = '.content-header h2,.dashboard-welcome h2,.gc-workspace-header h2,.dashboard-plans-heading h2,.public-plans-heading h2,#hero-title > span,#resources-title,#access-title';
const surfaceSelector = '.dashboard-welcome,.gc-workspace-header,.marketing .resource-card,.plan-card,.tab-content > .card';
let shutdown;

function boot() {
  if (shutdown) return;
  const signalController = new AbortController();
  const { signal } = signalController;
  const roots = new Map();
  const contexts = new Map();
  const energyFields = new Map();
  const interactions = gsap.context(() => {});
  const decorated = new WeakSet();
  const observedPanels = new WeakSet();
  const observedDialogs = new WeakSet();
  let lenis;
  let ticker;
  let unsubscribe;
  let scanFrame = 0;
  let refreshFrame = 0;
  let alive = true;
  document.documentElement.dataset.motionEngine = 'gsap';

  function refresh() {
    cancelAnimationFrame(refreshFrame);
    refreshFrame = requestAnimationFrame(() => {
      if (!alive) return;
      lenis?.resize();
      ScrollTrigger.refresh();
    });
  }

  function mountText(heading) {
    if (decorated.has(heading) || !heading.getClientRects().length) return;
    decorated.add(heading);
    const color = getComputedStyle(heading).color;
    // Keep existing icons, line breaks, labels and event handlers intact.
    for (const node of [...heading.childNodes]) {
      if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) continue;
      const text = node.textContent;
      const host = document.createElement('span');
      host.className = 'ui-shiny-host';
      node.replaceWith(host);
      const root = createRoot(host);
      const workspace = document.body.matches('[data-design="studio"]');
      flushSync(() => root.render(<ShinyText text={text} color={color} shineColor="#c3efff" trigger={workspace ? 'loop' : 'view'} speed={workspace ? 2.4 : 1.1} delay={workspace ? 1.8 : 0} shineWidth={workspace ? 55 : 24} />));
      roots.set(host, { root, text });
    }
  }

  function mountSurface(surface) {
    if (decorated.has(surface) || !surface.getClientRects().length || !fine.matches) return;
    decorated.add(surface);
    surface.classList.add('ui-surface');
    if (getComputedStyle(surface).position === 'static') surface.classList.add('ui-surface-static');
    const host = document.createElement('div');
    host.className = 'ui-spotlight-layer';
    host.setAttribute('aria-hidden', 'true');
    surface.append(host);
    const root = createRoot(host);
    const workspace = document.body.matches('[data-design="studio"]');
    flushSync(() => root.render(<SpotlightCard className="ui-spotlight" intensity={workspace ? 0.25 : 0.07} borderGlow={workspace ? 0.5 : 0.14} spotlightColor="#79bcff" spotlightSize={360} proximity={60} flare={true} ambient={workspace && surface.matches('.dashboard-welcome,.gc-workspace-header')} style={{ '--spotlight-card-surface': 'transparent', '--spotlight-card-shadow': 'none' }} />));
    roots.set(host, { root, surface });
  }

  function enterPanel(panel) {
    if (!panel.getClientRects().length) return;
    scan(panel);
    if (reduced.matches) return;
    contexts.get(panel)?.revert();
    const items = [...panel.querySelectorAll(':scope > .content-header,:scope > .dashboard-hero,:scope > .dashboard-grid > article,:scope > .card,:scope > .plans-grid > article,:scope > .gc-workspace-header,:scope > .gc-workspace-nav,:scope > #campaign-monitor')].slice(0, 12);
    const targets = items.length ? items : [...panel.children].filter(node => node.matches('header,section,form')).slice(0, 6);
    if (!targets.length) return;
    contexts.set(panel, gsap.context(() => {
      gsap.timeline({ defaults: { duration: 0.7, ease: 'power3.out' } })
        .from(targets, { y: 36, opacity: 0.12, stagger: 0.075, clearProps: 'transform,opacity' });
    }, panel));
  }

  function scan(scope = document) {
    if (!alive || reduced.matches) return;
    for (const [host, item] of roots) {
      if (!host.isConnected || (item.surface && !item.surface.getClientRects().length)) {
        item.root.unmount();
        if (item.surface) {
          item.surface.classList.remove('ui-surface', 'ui-surface-static');
          decorated.delete(item.surface);
          host.remove();
        }
        roots.delete(host);
      }
    }
    for (const [header, field] of energyFields) {
      if (!header.isConnected) { field.destroy(); energyFields.delete(header); }
    }
    scope.querySelectorAll(headingSelector).forEach(mountText);
    scope.querySelectorAll(surfaceSelector).forEach(mountSurface);
    if (document.body.matches('[data-design="studio"]')) {
      scope.querySelectorAll('.dashboard-welcome,.gc-workspace-header,.tab-content > .content-header').forEach(header => {
        if (energyFields.has(header)) return;
        const field = createEnergyField(header);
        if (field) energyFields.set(header, field);
      });
    }
    scope.querySelectorAll('.tab-content').forEach(panel => {
      if (observedPanels.has(panel)) return;
      observedPanels.add(panel);
      panelObserver.observe(panel, { attributes: true, attributeFilter: ['class'] });
    });
    scope.querySelectorAll('.modal,[role="dialog"]').forEach(dialog => {
      if (observedDialogs.has(dialog)) return;
      observedDialogs.add(dialog);
      dialogObserver.observe(dialog, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
    });
  }

  const dialogObserver = new MutationObserver(records => {
    for (const { target } of records) {
      if (!target.getClientRects().length || reduced.matches) continue;
      const content = target.querySelector('.modal-content') || target.firstElementChild;
      if (content) interactions.add(() => {
        gsap.fromTo(content, { y: 8, opacity: 0.5 }, { y: 0, opacity: 1, duration: 0.2, ease: 'power2.out', clearProps: 'transform,opacity', overwrite: true });
      });
    }
    refresh();
  });
  const panelObserver = new MutationObserver(records => {
    for (const record of records) {
      if (record.target.classList.contains('active')) enterPanel(record.target);
    }
    refresh();
  });
  const observer = new MutationObserver(records => {
    // Polling updates must not replay entrances or animate live numbers/logs.
    if (!records.some(record => [...record.addedNodes].some(node => node.nodeType === Node.ELEMENT_NODE && !node.closest?.('.ui-shiny-host,.ui-spotlight-layer,.gc-live-content,.logs')))) return;
    cancelAnimationFrame(scanFrame);
    scanFrame = requestAnimationFrame(() => scan());
  });

  if (!reduced.matches) {
    lenis = new Lenis({
      autoRaf: false,
      lerp: 0.16,
      smoothWheel: true,
      syncTouch: false,
      respectReducedMotion: true,
      stopInertiaOnNavigate: true,
      prevent: node => Boolean(node.closest('.sidebar,.modal,[role="dialog"],textarea,select,.logs,.gc-log-list,.table-responsive,.gc-sessions,[data-lenis-prevent]')),
    });
    unsubscribe = lenis.on('scroll', ScrollTrigger.update);
    ticker = seconds => {
      lenis.raf(seconds * 1000);
      energyFields.forEach(field => field.draw(seconds));
    };
    gsap.ticker.add(ticker);
    gsap.ticker.lagSmoothing(0);
    scan();
    observer.observe(document.body, { childList: true, subtree: true });
    const active = document.querySelector('.tab-content.active');
    if (active) enterPanel(active);
    if (document.body.classList.contains('marketing')) {
      contexts.set(document.body, gsap.context(() => {
        const hero = document.querySelector('.hero__c');
        if (hero) gsap.timeline({ defaults: { ease: 'power3.out', duration: 0.5 } })
          .from(hero.children, { y: 16, opacity: 0.3, stagger: 0.07, clearProps: 'transform,opacity' });
        gsap.utils.toArray('.section-intro,.resource-card,.public-plans-heading,.access-copy').forEach(target => {
          gsap.from(target, { y: 18, opacity: 0.4, duration: 0.5, ease: 'power2.out', clearProps: 'transform,opacity', scrollTrigger: { trigger: target, start: 'top 94%', once: true } });
        });
      }, document.body));
    }
  }

  document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const tab = event.target.closest('.menu-item[data-tab]');
    if (tab && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      // Existing navigation intentionally resets scroll. Cancel any wheel inertia too.
      lenis?.scrollTo(0, { immediate: true });
    }
    const link = event.target.closest('a[href^="#"]');
    if (!tab && link && !event.defaultPrevented && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !link.download && !link.target) {
      const id = link.getAttribute('href').slice(1);
      const target = id && document.getElementById(id);
      if (target && target.getClientRects().length && lenis) {
        event.preventDefault();
        history.pushState(null, '', '#' + id);
        const previous = target.getAttribute('tabindex');
        target.tabIndex = -1;
        target.focus({ preventScroll: true });
        // Retain focusability until blur: removing tabindex immediately makes
        // Chromium return focus to body before keyboard navigation can continue.
        if (previous === null) target.addEventListener('blur', () => target.removeAttribute('tabindex'), { once: true, signal });
        lenis.scrollTo(target, { offset: -76, duration: 0.7 });
      }
    }
  }, { signal });
  document.addEventListener('toggle', event => {
    if (event.target instanceof HTMLDetailsElement && event.target.open) {
      const content = [...event.target.children].filter(node => node.tagName !== 'SUMMARY');
      if (!reduced.matches && content.length) {
        interactions.add(() => gsap.fromTo(content, { opacity: 0.5 }, { opacity: 1, duration: 0.18, clearProps: 'opacity', overwrite: true }));
      }
    }
    refresh();
  }, { capture: true, signal });
  window.addEventListener('resize', refresh, { passive: true, signal });
  document.fonts?.ready.then(() => { if (alive) refresh(); });
  refresh();

  shutdown = () => {
    alive = false;
    signalController.abort();
    observer.disconnect();
    panelObserver.disconnect();
    dialogObserver.disconnect();
    cancelAnimationFrame(scanFrame);
    cancelAnimationFrame(refreshFrame);
    contexts.forEach(context => context.revert());
    interactions.revert();
    energyFields.forEach(field => field.destroy());
    if (ticker) gsap.ticker.remove(ticker);
    unsubscribe?.();
    lenis?.destroy();
    for (const [host, item] of roots) {
      item.root.unmount();
      if (item.surface) {
        item.surface.classList.remove('ui-surface', 'ui-surface-static');
        host.remove();
      } else if (host.isConnected) host.replaceWith(document.createTextNode(item.text));
    }
    roots.clear();
    shutdown = null;
  };
  // Small diagnostics surface for local browser verification, with no user data.
  window.TGInterface = { engine: 'gsap', reactBits: true, get smoothScroll() { return Boolean(lenis); }, dispose: () => shutdown?.() };
}

reduced.addEventListener('change', () => { shutdown?.(); boot(); });
fine.addEventListener('change', () => { shutdown?.(); boot(); });
window.addEventListener('pagehide', () => shutdown?.());
window.addEventListener('pageshow', () => boot());
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
else boot();
