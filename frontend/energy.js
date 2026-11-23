// Decorative constellation, driven by the shared GSAP ticker, never a second RAF loop.
export function createEnergyField(header) {
  const canvas = document.createElement('canvas');
  canvas.className = 'ui-energy-field';
  canvas.setAttribute('aria-hidden', 'true');
  header.classList.add('ui-energy-header');
  header.append(canvas);
  const ctx = canvas.getContext('2d');
  if (!ctx) { canvas.remove(); header.classList.remove('ui-energy-header'); return null; }
  let width = 0, height = 0, visible = false, last = 0;
  const marketing = header.matches('.marketing .hero');
  const dots = Array.from({ length: marketing ? (innerWidth < 680 ? 28 : 65) : (innerWidth < 680 ? 15 : 28) }, () => ({
    x: Math.random(), y: Math.random(), vx: (Math.random() - 0.5) * 0.035,
    vy: (Math.random() - 0.5) * 0.1, size: 1 + Math.random() * 1.7,
  }));
  const resize = new ResizeObserver(() => {
    width = header.clientWidth; height = header.clientHeight;
    const ratio = Math.min(devicePixelRatio || 1, 1.5);
    canvas.width = width * ratio; canvas.height = height * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  });
  const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; last = 0; });
  resize.observe(header); visibility.observe(header);
  return {
    draw(time) {
      if (!visible || document.hidden || !width || !height) { last = 0; return; }
      const dt = last ? Math.min(0.05, time - last) : 0;
      last = time;
      ctx.clearRect(0, 0, width, height);
      for (const dot of dots) {
        dot.x = (dot.x + dot.vx * dt + 1) % 1;
        dot.y = (dot.y + dot.vy * dt + 1) % 1;
        ctx.beginPath(); ctx.arc(dot.x * width, dot.y * height, dot.size, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(113,199,255,0.65)'; ctx.fill();
      }
      for (let i = 0; i < dots.length; i++) for (let j = i + 1; j < dots.length; j++) {
        const a = dots[i], b = dots[j];
        const distance = Math.hypot((a.x - b.x) * width, (a.y - b.y) * height);
        if (distance > (marketing ? 200 : 140)) continue;
        ctx.strokeStyle = `rgba(99,165,255,${(1 - distance / (marketing ? 200 : 140)) * 0.2})`;
        ctx.beginPath(); ctx.moveTo(a.x * width, a.y * height); ctx.lineTo(b.x * width, b.y * height); ctx.stroke();
      }
    },
    destroy() { resize.disconnect(); visibility.disconnect(); canvas.remove(); header.classList.remove('ui-energy-header'); },
  };
}
