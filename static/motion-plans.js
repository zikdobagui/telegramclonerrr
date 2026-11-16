/* Presentation only: never starts operations or changes subscription data. */
(() => {
 'use strict';
 const root = document.documentElement;
 const reduced = matchMedia('(prefers-reduced-motion: reduce)');
 // Motion follows the operating system; no visible pause control or stored pause state.
 root.removeAttribute('data-motion-paused');
 function sync() {
  if (reduced.matches) document.getAnimations().forEach(animation => animation.cancel());
 }
 reduced.addEventListener('change', sync);
 function enterPanel(panel) {
  if (!panel || reduced.matches) return;
  const items = panel.querySelectorAll(':scope > .dashboard-grid > article, :scope > .plans-grid > article, :scope > .dashboard-plans .plans-grid > article');
  items.forEach((item, index) => item.animate([
   {opacity:.2,translate:'0 32px'},
   {opacity:1,translate:'0 0'}
  ], {duration:850,delay:index*110,easing:'cubic-bezier(.2,.8,.2,1)',fill:'backwards'}));
 }
 document.querySelectorAll('.menu-item[data-tab]').forEach(link => link.addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  enterPanel(document.getElementById(link.dataset.tab));
 }));
 enterPanel(document.querySelector('.tab-content.active'));
 const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
 document.querySelectorAll('.plan-card,.marketing .resource-card,#dashboard .dashboard-card').forEach(card => {
  let frame = 0;
  function reset() {
   cancelAnimationFrame(frame);
   card.style.removeProperty('--rx');card.style.removeProperty('--ry');
   card.style.removeProperty('--light-x');card.style.removeProperty('--light-y');
  }
  card.addEventListener('pointermove', event => {
   if (reduced.matches || !finePointer.matches) return;
   const rect = card.getBoundingClientRect();
   const x = Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width));
   const y = Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height));
   cancelAnimationFrame(frame);
   frame = requestAnimationFrame(() => {
    card.style.setProperty('--rx', `${(0.5-y)*8}deg`);
    card.style.setProperty('--ry', `${(x-0.5)*10}deg`);
    card.style.setProperty('--light-x', `${x*100}%`);
    card.style.setProperty('--light-y', `${y*100}%`);
   });
  });
  card.addEventListener('pointerleave', reset);
  card.addEventListener('pointercancel', reset);
  reduced.addEventListener('change', reset);
  finePointer.addEventListener('change', reset);
 });
 document.querySelectorAll('[data-plan-detail]').forEach(button => button.addEventListener('click', () => {
  const detail = document.getElementById(button.getAttribute('aria-controls'));
  if (!detail) return;
  const open = button.getAttribute('aria-expanded') !== 'true';
  button.setAttribute('aria-expanded', String(open));detail.hidden = !open;
  button.textContent = open ? 'Fechar exemplo' : 'Ver exemplo';
 }));
})();
