(function () {
    const canvas = document.getElementById('panel-3d-bg');
    if (!canvas) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;

    if (!window.THREE) {
        window.__panel3dState = { mode: 'canvas2d', renderedFrames: 0 };
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let width = 0;
        let height = 0;
        const nodes = Array.from({ length: 78 }, (_, index) => ({
            x: Math.random(),
            y: Math.random(),
            z: 0.25 + Math.random() * 0.75,
            hue: index % 3
        }));

        function resize2d() {
            width = window.innerWidth;
            height = window.innerHeight;
            const ratio = Math.min(window.devicePixelRatio || 1, 1.8);
            canvas.width = Math.floor(width * ratio);
            canvas.height = Math.floor(height * ratio);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        }

        function draw2d(time) {
            requestAnimationFrame(draw2d);
            window.__panel3dState.renderedFrames += 1;
            ctx.clearRect(0, 0, width, height);
            const gradient = ctx.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, '#07111f');
            gradient.addColorStop(0.48, '#102033');
            gradient.addColorStop(1, '#07131b');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, width, height);

            const t = time * 0.00008;
            nodes.forEach((node, index) => {
                const x = (node.x * width + Math.sin(t * 8 + index) * 34 * node.z) % width;
                const y = (node.y * height + Math.cos(t * 7 + index * 0.8) * 24 * node.z) % height;
                const radius = 1 + node.z * 2.2;
                ctx.beginPath();
                ctx.fillStyle = node.hue === 0 ? 'rgba(56,189,248,.75)' : node.hue === 1 ? 'rgba(34,197,94,.62)' : 'rgba(249,115,22,.55)';
                ctx.arc(x, y, radius, 0, Math.PI * 2);
                ctx.fill();

                for (let j = index + 1; j < Math.min(nodes.length, index + 5); j += 1) {
                    const other = nodes[j];
                    const ox = (other.x * width + Math.sin(t * 8 + j) * 34 * other.z) % width;
                    const oy = (other.y * height + Math.cos(t * 7 + j * 0.8) * 24 * other.z) % height;
                    const distance = Math.hypot(x - ox, y - oy);
                    if (distance < 170) {
                        ctx.strokeStyle = `rgba(125,211,252,${(1 - distance / 170) * 0.18})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(x, y);
                        ctx.lineTo(ox, oy);
                        ctx.stroke();
                    }
                }
            });
        }

        resize2d();
        window.addEventListener('resize', resize2d);
        requestAnimationFrame(draw2d);
        return;
    }

    window.__panel3dState = { mode: 'three', renderedFrames: 0 };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0.5, 8);

    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true,
        powerPreference: 'high-performance'
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8));
    renderer.setSize(window.innerWidth, window.innerHeight, false);

    const group = new THREE.Group();
    scene.add(group);

    const particles = 220;
    const positions = new Float32Array(particles * 3);
    const colors = new Float32Array(particles * 3);
    const palette = [
        new THREE.Color('#38bdf8'),
        new THREE.Color('#22c55e'),
        new THREE.Color('#f97316'),
        new THREE.Color('#e2e8f0')
    ];

    for (let i = 0; i < particles; i += 1) {
        const i3 = i * 3;
        positions[i3] = (Math.random() - 0.5) * 14;
        positions[i3 + 1] = (Math.random() - 0.5) * 8;
        positions[i3 + 2] = (Math.random() - 0.5) * 8;
        const color = palette[i % palette.length];
        colors[i3] = color.r;
        colors[i3 + 1] = color.g;
        colors[i3 + 2] = color.b;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
        size: 0.035,
        vertexColors: true,
        transparent: true,
        opacity: 0.72,
        depthWrite: false
    });

    const points = new THREE.Points(particleGeometry, particleMaterial);
    group.add(points);

    const ringGeometry = new THREE.TorusGeometry(2.2, 0.012, 12, 120);
    const ringMaterial = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.24
    });

    const rings = [];
    for (let i = 0; i < 4; i += 1) {
        const ring = new THREE.Mesh(ringGeometry, ringMaterial.clone());
        ring.position.set(2.8 - i * 1.15, 0.55 - i * 0.35, -1.2 - i * 0.4);
        ring.rotation.set(1.05 + i * 0.16, 0.25 + i * 0.2, 0.55);
        ring.scale.setScalar(1 + i * 0.24);
        ring.material.opacity = 0.22 - i * 0.035;
        rings.push(ring);
        group.add(ring);
    }

    const lineMaterial = new THREE.LineBasicMaterial({
        color: 0x7dd3fc,
        transparent: true,
        opacity: 0.16
    });
    const lineGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array([
        -6.5, -2.6, -1.8,
        -3.8, -0.7, -1.2,
        -1.4, -1.45, -0.9,
        1.2, 0.6, -1.3,
        4.8, -0.3, -2.1
    ]);
    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    const line = new THREE.Line(lineGeometry, lineMaterial);
    group.add(line);

    let mouseX = 0;
    let mouseY = 0;
    let visible = true;

    window.addEventListener('pointermove', (event) => {
        mouseX = (event.clientX / window.innerWidth - 0.5) * 0.55;
        mouseY = (event.clientY / window.innerHeight - 0.5) * 0.35;
    }, {passive: true});

    document.addEventListener('visibilitychange', () => {
        visible = document.visibilityState === 'visible';
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight, false);
    });

    function animate(time) {
        requestAnimationFrame(animate);
        if (!visible) return;

        const t = time * 0.00018;
        group.rotation.y = t + mouseX;
        group.rotation.x = -0.08 + mouseY;
        points.rotation.z = -t * 0.35;
        rings.forEach((ring, index) => {
            ring.rotation.z += 0.0016 + index * 0.00035;
            ring.rotation.x += 0.0005;
        });

        renderer.render(scene, camera);
        window.__panel3dState.renderedFrames += 1;
    }

    requestAnimationFrame(animate);
})();
