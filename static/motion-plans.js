/* Presentation only: never starts operations or changes subscription data. */
(() => {
 'use strict';
 const root = document.documentElement;
 const reduced = matchMedia('(prefers-reduced-motion: reduce)');
 let paused = false;
 try { paused = localStorage.getItem('tgMotionPaused') === '1'; } catch (_) {}
 const slot = document.querySelector('.dashboard-actions, .marketing .hero .hero__c');
 let toggle;
 function sync() {
  root.toggleAttribute('data-motion-paused', paused);
  if (toggle) {
   toggle.textContent = paused ? 'Retomar animações' : 'Pausar animações';
   toggle.setAttribute('aria-pressed', String(paused));
  }
  if (paused || reduced.matches) document.getAnimations().forEach(animation => {
   if (animation.effect?.getTiming().iterations !== Infinity) animation.finish();
  });
 }
 if (slot) {
  toggle = document.createElement('button');
  toggle.type = 'button';toggle.className = 'motion-toggle';
  toggle.addEventListener('click', () => {
   paused = !paused;
   try { localStorage.setItem('tgMotionPaused', paused ? '1' : '0'); } catch (_) {}
   sync();
  });
  slot.append(toggle);
 }
 sync();
 reduced.addEventListener('change', sync);
 function enterPanel(panel) {
  if (!panel || paused || reduced.matches) return;
  const items = panel.querySelectorAll(':scope > .dashboard-grid > article, :scope > .plans-grid > article');
  items.forEach((item, index) => item.animate([
   {opacity:.2,transform:'translateY(16px)'},
   {opacity:1,transform:'translateY(0)'}
  ], {duration:500,delay:index*65,easing:'cubic-bezier(.2,.8,.2,1)',fill:'backwards'}));
 }
 document.querySelectorAll('.menu-item[data-tab]').forEach(link => link.addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  enterPanel(document.getElementById(link.dataset.tab));
 }));
 enterPanel(document.querySelector('.tab-content.active'));
 document.querySelectorAll('[data-plan-detail]').forEach(button => button.addEventListener('click', () => {
  const detail = document.getElementById(button.getAttribute('aria-controls'));
  if (!detail) return;
  const open = button.getAttribute('aria-expanded') !== 'true';
  button.setAttribute('aria-expanded', String(open));detail.hidden = !open;
  button.textContent = open ? 'Fechar exemplo' : 'Ver exemplo';
 }));
})();
