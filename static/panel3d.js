(function () {
    if (window.__panelEffectLoaded) return;
    window.__panelEffectLoaded = true;

    const canvas = document.getElementById('panel-3d-bg');
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const state = {
        width: 0,
        height: 0,
        ratio: 1,
        visible: true,
        snowEnabled: !reducedMotion && localStorage.getItem('panelSnowEnabled') !== 'false',
        frames: 0,
        lastFrame: 0,
        flakes: []
    };
    window.__panel3dState = { mode: 'nested-grid-snow', renderedFrames: 0 };

    function createFlakes() {
        const total = state.width < 760 ? 34 : 64;
        state.flakes = Array.from({ length: total }, () => ({
            x: Math.random() * state.width,
            y: Math.random() * state.height,
            radius: 0.7 + Math.random() * 1.7,
            speed: 0.22 + Math.random() * 0.48,
            drift: (Math.random() - 0.5) * 0.22,
            opacity: 0.18 + Math.random() * 0.42
        }));
    }

    function resize() {
        const panelZoom = parseFloat(window.getComputedStyle(document.body).zoom) || 1;
        state.width = window.innerWidth / panelZoom;
        state.height = window.innerHeight / panelZoom;
        state.ratio = Math.min(window.devicePixelRatio || 1, 1.35);
        canvas.width = Math.floor(state.width * state.ratio);
        canvas.height = Math.floor(state.height * state.ratio);
        canvas.style.width = `${state.width}px`;
        canvas.style.height = `${state.height}px`;
        ctx.setTransform(state.ratio, 0, 0, state.ratio, 0, 0);
        createFlakes();
    }

    function drawBackground(time) {
        const gradient = ctx.createLinearGradient(0, 0, state.width, state.height);
        gradient.addColorStop(0, '#06101d');
        gradient.addColorStop(0.52, '#0a1929');
        gradient.addColorStop(1, '#06151c');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, state.width, state.height);

        const centerX = state.width * 0.58;
        const centerY = state.height * 0.48;
        const maxSize = Math.max(state.width, state.height) * 1.35;
        const pulse = Math.sin(time * 0.00018) * 5;
        ctx.lineWidth = 1;

        for (let size = 90, index = 0; size < maxSize; size += 68, index += 1) {
            const alpha = Math.max(0.018, 0.105 - index * 0.004);
            ctx.strokeStyle = `rgba(125, 211, 252, ${alpha})`;
            ctx.strokeRect(
                centerX - (size + pulse) / 2,
                centerY - (size + pulse) / 2,
                size + pulse,
                size + pulse
            );
        }

        ctx.strokeStyle = 'rgba(148, 163, 184, 0.055)';
        const gridGap = 72;
        for (let x = 0; x < state.width; x += gridGap) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, state.height);
            ctx.stroke();
        }
        for (let y = 0; y < state.height; y += gridGap) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(state.width, y);
            ctx.stroke();
        }
    }

    function drawSnow() {
        if (!state.snowEnabled) return;
        state.flakes.forEach((flake) => {
            flake.y += flake.speed;
            flake.x += flake.drift;
            if (flake.y > state.height + 4) {
                flake.y = -4;
                flake.x = Math.random() * state.width;
            }
            if (flake.x < -4) flake.x = state.width + 4;
            if (flake.x > state.width + 4) flake.x = -4;

            ctx.fillStyle = `rgba(235, 248, 255, ${flake.opacity})`;
            ctx.beginPath();
            ctx.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    function animate(time) {
        requestAnimationFrame(animate);
        if (!state.visible || time - state.lastFrame < 50) return;
        state.lastFrame = time;
        ctx.clearRect(0, 0, state.width, state.height);
        drawBackground(time);
        drawSnow();
        state.frames += 1;
        window.__panel3dState.renderedFrames = state.frames;
    }

    window.addEventListener('panel-snow-change', (event) => {
        state.snowEnabled = Boolean(event.detail && event.detail.enabled) && !reducedMotion;
    });
    document.addEventListener('visibilitychange', () => {
        state.visible = document.visibilityState === 'visible';
    });
    window.addEventListener('resize', resize, { passive: true });

    resize();
    requestAnimationFrame(animate);
})();
