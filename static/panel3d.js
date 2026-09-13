(function () {
    if (window.__panelEffectLoaded) return;
    window.__panelEffectLoaded = true;

    const canvas = document.getElementById('panel-3d-bg');
    if (!canvas) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx || reducedMotion) return;

    const state = {
        width: 0,
        height: 0,
        ratio: 1,
        visible: true,
        frames: 0,
        lastFrame: 0,
        nodes: []
    };
    window.__panel3dState = { mode: 'light-effect', renderedFrames: 0 };

    function createNodes() {
        const total = window.innerWidth < 760 ? 28 : 52;
        state.nodes = Array.from({ length: total }, (_, index) => ({
            x: Math.random(),
            y: Math.random(),
            depth: 0.35 + Math.random() * 0.65,
            speed: 0.16 + Math.random() * 0.28,
            color: index % 3
        }));
    }

    function resize() {
        state.width = window.innerWidth;
        state.height = window.innerHeight;
        state.ratio = Math.min(window.devicePixelRatio || 1, 1.35);
        canvas.width = Math.floor(state.width * state.ratio);
        canvas.height = Math.floor(state.height * state.ratio);
        canvas.style.width = `${state.width}px`;
        canvas.style.height = `${state.height}px`;
        ctx.setTransform(state.ratio, 0, 0, state.ratio, 0, 0);
        createNodes();
    }

    function drawBackground() {
        const gradient = ctx.createLinearGradient(0, 0, state.width, state.height);
        gradient.addColorStop(0, '#07111f');
        gradient.addColorStop(0.48, '#0c1a2b');
        gradient.addColorStop(1, '#07131b');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, state.width, state.height);

        ctx.strokeStyle = 'rgba(125, 211, 252, 0.045)';
        ctx.lineWidth = 1;
        const gap = 54;
        for (let x = 0; x <= state.width; x += gap) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, state.height);
            ctx.stroke();
        }
        for (let y = 0; y <= state.height; y += gap) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(state.width, y);
            ctx.stroke();
        }
    }

    function drawNodes(time) {
        const t = time * 0.00008;
        const points = state.nodes.map((node, index) => ({
            x: (node.x * state.width + Math.sin(t * node.speed * 16 + index) * 22 * node.depth + state.width) % state.width,
            y: (node.y * state.height + Math.cos(t * node.speed * 12 + index) * 18 * node.depth + state.height) % state.height,
            depth: node.depth,
            color: node.color
        }));

        points.forEach((point, index) => {
            for (let j = index + 1; j < Math.min(points.length, index + 4); j += 1) {
                const other = points[j];
                const distance = Math.hypot(point.x - other.x, point.y - other.y);
                if (distance < 145) {
                    ctx.strokeStyle = `rgba(125, 211, 252, ${(1 - distance / 145) * 0.13})`;
                    ctx.beginPath();
                    ctx.moveTo(point.x, point.y);
                    ctx.lineTo(other.x, other.y);
                    ctx.stroke();
                }
            }

            const color = point.color === 0
                ? 'rgba(56, 189, 248, 0.58)'
                : point.color === 1
                    ? 'rgba(34, 197, 94, 0.42)'
                    : 'rgba(249, 115, 22, 0.34)';
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(point.x, point.y, 1.2 + point.depth * 1.5, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    function animate(time) {
        requestAnimationFrame(animate);
        if (!state.visible || time - state.lastFrame < 66) return;
        state.lastFrame = time;

        ctx.clearRect(0, 0, state.width, state.height);
        drawBackground();
        drawNodes(time);
        state.frames += 1;
        window.__panel3dState.renderedFrames = state.frames;
    }

    document.addEventListener('visibilitychange', () => {
        state.visible = document.visibilityState === 'visible';
    });
    window.addEventListener('resize', resize, { passive: true });

    resize();
    requestAnimationFrame(animate);
})();
