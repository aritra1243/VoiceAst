import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/* =========================================================================
   IRON MAN JARVIS 3D HELMET & ARC REACTOR CORE (WebGL via Three.js)
   Renders a 3D cybernetic Iron Man bust with glowing cyan eyes,
   an Arc Reactor chest core, holographic wireframes, and animated talking jaw.
   ========================================================================= */

export default function ScannerCore({ isListening, isTalking = false, wsStatus }) {
  const containerRef = useRef(null);

  // Smooth animation targets
  const stateRef = useRef({
    isTalking,
    isListening,
    mouseX: 0,
    mouseY: 0,
    targetRotationX: 0,
    targetRotationY: 0,
  });

  // Keep stateRef up to date
  useEffect(() => {
    stateRef.current.isTalking = isTalking;
    stateRef.current.isListening = isListening;
  }, [isTalking, isListening]);

  // Track mouse for 3D head look-at
  useEffect(() => {
    const handleMouseMove = (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      stateRef.current.mouseX = (e.clientX - cx) / cx; // -1 to +1
      stateRef.current.mouseY = (e.clientY - cy) / cy;
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = 340;
    const height = 380;

    // ── 1. Scene, Camera, Renderer ──
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // ── 2. Color Palette ──
    const CYAN = 0x00f7ff;
    const AMBER = 0xffaa00;
    const DARK_STEEL = 0x0a1628;
    const ARMOR_BLUE = 0x0d2240;
    const RED_ACCENT = 0xff2255;

    // ── 3. Lights ──
    const ambientLight = new THREE.AmbientLight(0x051525, 2.5);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(CYAN, 3.0);
    mainLight.position.set(5, 8, 5);
    scene.add(mainLight);

    const rimLight = new THREE.DirectionalLight(RED_ACCENT, 2.0);
    rimLight.position.set(-5, -2, -3);
    scene.add(rimLight);

    // Eye glow point light
    const eyeLight = new THREE.PointLight(CYAN, 4.0, 4);
    eyeLight.position.set(0, 0.8, 1.2);
    scene.add(eyeLight);

    // Arc reactor glow light
    const arcLight = new THREE.PointLight(CYAN, 6.0, 5);
    arcLight.position.set(0, -1.8, 1.5);
    scene.add(arcLight);

    // ── 4. Main 3D Root Group ──
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // ── 5. Materials ──
    const metalMaterial = new THREE.MeshStandardMaterial({
      color: DARK_STEEL,
      roughness: 0.35,
      metalness: 0.85,
    });

    const plateMaterial = new THREE.MeshStandardMaterial({
      color: ARMOR_BLUE,
      roughness: 0.25,
      metalness: 0.9,
    });

    const glowCyanMaterial = new THREE.MeshBasicMaterial({
      color: CYAN,
      transparent: true,
      opacity: 0.95,
    });

    const wireCyanMaterial = new THREE.MeshBasicMaterial({
      color: CYAN,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });

    const wireRedMaterial = new THREE.MeshBasicMaterial({
      color: RED_ACCENT,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
    });

    // ── 6. Build Iron Man Helmet ──
    const helmetGroup = new THREE.Group();
    helmetGroup.position.set(0, 0.4, 0);
    rootGroup.add(helmetGroup);

    // Upper Cranium (Dome)
    const domeGeo = new THREE.SphereGeometry(1.0, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.55);
    domeGeo.scale(0.92, 1.1, 1.05);
    const craniumMesh = new THREE.Mesh(domeGeo, metalMaterial);
    helmetGroup.add(craniumMesh);

    // Cranium Wireframe Overlay
    const craniumWire = new THREE.Mesh(domeGeo, wireCyanMaterial);
    craniumWire.scale.set(1.01, 1.01, 1.01);
    helmetGroup.add(craniumWire);

    // Brow / Forehead Plate
    const browGeo = new THREE.BoxGeometry(1.65, 0.35, 0.4);
    const browMesh = new THREE.Mesh(browGeo, plateMaterial);
    browMesh.position.set(0, 0.85, 0.85);
    browMesh.rotation.x = -0.25;
    helmetGroup.add(browMesh);

    // Brow Central Crest
    const crestGeo = new THREE.ConeGeometry(0.2, 0.6, 4);
    const crestMesh = new THREE.Mesh(crestGeo, glowCyanMaterial);
    crestMesh.position.set(0, 1.15, 0.88);
    crestMesh.rotation.x = 0.2;
    helmetGroup.add(crestMesh);

    // Cheeks & Temple Side Plates
    [-1, 1].forEach((side) => {
      const cheekGeo = new THREE.BoxGeometry(0.45, 0.8, 0.7);
      const cheekMesh = new THREE.Mesh(cheekGeo, plateMaterial);
      cheekMesh.position.set(side * 0.82, 0.35, 0.55);
      cheekMesh.rotation.y = side * -0.3;
      cheekMesh.rotation.z = side * 0.15;
      helmetGroup.add(cheekMesh);

      // Temple Wireframe Accent
      const templeWire = new THREE.Mesh(cheekGeo, wireRedMaterial);
      templeWire.position.copy(cheekMesh.position);
      templeWire.rotation.copy(cheekMesh.rotation);
      templeWire.scale.set(1.03, 1.03, 1.03);
      helmetGroup.add(templeWire);
    });

    // Nose Bridge
    const noseGeo = new THREE.ConeGeometry(0.18, 0.6, 4);
    const noseMesh = new THREE.Mesh(noseGeo, metalMaterial);
    noseMesh.position.set(0, 0.45, 1.02);
    noseMesh.rotation.x = 0.3;
    helmetGroup.add(noseMesh);

    // ── 7. GLOWING CYAN EYES ──
    const eyeGroup = new THREE.Group();
    helmetGroup.add(eyeGroup);

    [-0.38, 0.38].forEach((xPos) => {
      // Slanted Iron Man eye shape using BoxGeometry scaled & rotated
      const eyeGeo = new THREE.BoxGeometry(0.42, 0.09, 0.12);
      const eyeMesh = new THREE.Mesh(eyeGeo, glowCyanMaterial);
      eyeMesh.position.set(xPos, 0.62, 0.96);
      eyeMesh.rotation.z = (xPos > 0 ? -1 : 1) * 0.22;
      eyeGroup.add(eyeMesh);

      // Outer Eye Glow Frame
      const eyeFrameGeo = new THREE.BoxGeometry(0.48, 0.14, 0.08);
      const eyeFrameMesh = new THREE.Mesh(eyeFrameGeo, metalMaterial);
      eyeFrameMesh.position.set(xPos, 0.62, 0.94);
      eyeFrameMesh.rotation.z = eyeMesh.rotation.z;
      eyeGroup.add(eyeFrameMesh);
    });

    // ── 8. ANIMATED JAW & MOUTH FACEPLATE ──
    const jawGroup = new THREE.Group();
    jawGroup.position.set(0, 0.1, 0.4); // Pivot point for mouth opening
    helmetGroup.add(jawGroup);

    // Lower Chin Plate
    const chinShape = new THREE.CylinderGeometry(0.68, 0.45, 0.75, 6);
    const chinMesh = new THREE.Mesh(chinShape, plateMaterial);
    chinMesh.position.set(0, -0.4, 0.45);
    chinMesh.rotation.y = Math.PI / 6;
    jawGroup.add(chinMesh);

    // Chin Wireframe
    const chinWire = new THREE.Mesh(chinShape, wireCyanMaterial);
    chinWire.position.copy(chinMesh.position);
    chinWire.rotation.copy(chinMesh.rotation);
    chinWire.scale.set(1.02, 1.02, 1.02);
    jawGroup.add(chinWire);

    // Mouth Speaker Grill (glowing slot underneath upper mask)
    const mouthGrillGeo = new THREE.BoxGeometry(0.65, 0.1, 0.15);
    const mouthGrillMesh = new THREE.Mesh(mouthGrillGeo, glowCyanMaterial);
    mouthGrillMesh.position.set(0, -0.08, 0.55);
    jawGroup.add(mouthGrillMesh);

    // ── 9. NECK & COLLAR (RED ACCENT BLUEPRINT) ──
    const neckGroup = new THREE.Group();
    neckGroup.position.set(0, -0.85, 0);
    rootGroup.add(neckGroup);

    const neckGeo = new THREE.CylinderGeometry(0.55, 0.7, 0.6, 12);
    const neckMesh = new THREE.Mesh(neckGeo, metalMaterial);
    neckGroup.add(neckMesh);

    const neckWire = new THREE.Mesh(neckGeo, wireRedMaterial);
    neckWire.scale.set(1.03, 1.03, 1.03);
    neckGroup.add(neckWire);

    // Collar Collarbone Ribs
    [-0.55, 0.55].forEach((xSide) => {
      const ribGeo = new THREE.TorusGeometry(0.4, 0.04, 8, 16, Math.PI);
      const ribMesh = new THREE.Mesh(ribGeo, wireRedMaterial);
      ribMesh.position.set(xSide * 0.6, -0.2, 0.3);
      ribMesh.rotation.z = xSide * 0.8;
      neckGroup.add(ribMesh);
    });

    // ── 10. CHEST ARMOR BUST & ARC REACTOR ──
    const chestGroup = new THREE.Group();
    chestGroup.position.set(0, -1.8, 0);
    rootGroup.add(chestGroup);

    // Main Chest Plate
    const chestGeo = new THREE.BoxGeometry(2.4, 1.1, 1.2);
    const chestMesh = new THREE.Mesh(chestGeo, metalMaterial);
    chestGroup.add(chestMesh);

    const chestWire = new THREE.Mesh(chestGeo, wireCyanMaterial);
    chestWire.scale.set(1.01, 1.01, 1.01);
    chestGroup.add(chestWire);

    // Shoulder Pads
    [-1.4, 1.4].forEach((side) => {
      const shoulderGeo = new THREE.SphereGeometry(0.55, 12, 12);
      shoulderGeo.scale(1.2, 0.7, 1.0);
      const shoulderMesh = new THREE.Mesh(shoulderGeo, plateMaterial);
      shoulderMesh.position.set(side, 0.35, 0);
      chestGroup.add(shoulderMesh);
    });

    // ── ARC REACTOR ──
    const arcGroup = new THREE.Group();
    arcGroup.position.set(0, 0.05, 0.62);
    chestGroup.add(arcGroup);

    // Outer Ring
    const outerRingGeo = new THREE.TorusGeometry(0.38, 0.04, 16, 32);
    const outerRingMesh = new THREE.Mesh(outerRingGeo, glowCyanMaterial);
    arcGroup.add(outerRingMesh);

    // Inner Ring
    const innerRingGeo = new THREE.TorusGeometry(0.24, 0.03, 16, 24);
    const innerRingMesh = new THREE.Mesh(innerRingGeo, glowCyanMaterial);
    arcGroup.add(innerRingMesh);

    // Core Glowing Sphere
    const coreGeo = new THREE.SphereGeometry(0.16, 16, 16);
    const coreMesh = new THREE.Mesh(coreGeo, glowCyanMaterial);
    arcGroup.add(coreMesh);

    // Arc Reactor Vanes / Triangular Nodes
    for (let i = 0; i < 10; i++) {
      const angle = (i * Math.PI * 2) / 10;
      const vaneGeo = new THREE.BoxGeometry(0.04, 0.12, 0.04);
      const vaneMesh = new THREE.Mesh(vaneGeo, wireCyanMaterial);
      vaneMesh.position.set(Math.cos(angle) * 0.31, Math.sin(angle) * 0.31, 0);
      vaneMesh.rotation.z = angle;
      arcGroup.add(vaneMesh);
    }

    // ── 11. HOLOGRAPHIC BACKGROUND PARTICLES ──
    const particleCount = 120;
    const particleGeo = new THREE.BufferGeometry();
    const posArray = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      posArray[i] = (Math.random() - 0.5) * 12;
      posArray[i + 1] = (Math.random() - 0.5) * 12;
      posArray[i + 2] = (Math.random() - 0.5) * 8 - 2;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.04,
      color: CYAN,
      transparent: true,
      opacity: 0.6,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // ── 12. ANIMATION LOOP ──
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();
      const state = stateRef.current;

      // Color shift when listening / processing
      const targetColor = state.isListening ? AMBER : CYAN;
      glowCyanMaterial.color.setHex(targetColor);
      eyeLight.color.setHex(targetColor);
      arcLight.color.setHex(targetColor);

      // Smooth Head Tracking to Mouse
      state.targetRotationY += (state.mouseX * 0.45 - state.targetRotationY) * 0.08;
      state.targetRotationX += (state.mouseY * 0.25 - state.targetRotationX) * 0.08;

      rootGroup.rotation.y = state.targetRotationY;
      rootGroup.rotation.x = state.targetRotationX;

      // Subtle Idle Floating Bob
      rootGroup.position.y = Math.sin(elapsedTime * 1.8) * 0.08;
      helmetGroup.rotation.z = Math.sin(elapsedTime * 1.2) * 0.02;

      // ── TALKING JAW ANIMATION ──
      if (state.isTalking) {
        // Dynamic jaw opening (rotates jaw group on X axis)
        const mouthOpen = Math.abs(Math.sin(elapsedTime * 14)) * 0.28 + 0.05;
        jawGroup.rotation.x = mouthOpen;

        // Pulse intensity of eyes and arc reactor
        const pulse = 4.0 + Math.sin(elapsedTime * 20) * 2.5;
        eyeLight.intensity = pulse;
        arcLight.intensity = pulse + 2.0;

        // Mouth grill brightness boost
        mouthGrillMesh.scale.set(1.0 + mouthOpen * 0.5, 1.0 + mouthOpen * 2.0, 1.0);
      } else {
        // Reset jaw to closed position
        jawGroup.rotation.x += (0 - jawGroup.rotation.x) * 0.15;
        eyeLight.intensity = 3.5;
        arcLight.intensity = 5.0;
        mouthGrillMesh.scale.set(1.0, 1.0, 1.0);
      }

      // Rotate Arc Reactor inner rings slowly
      arcGroup.rotation.z = elapsedTime * 0.8;
      outerRingMesh.rotation.z = -elapsedTime * 0.5;

      // Slow background particle drift
      particles.rotation.y = elapsedTime * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    // ── Cleanup ──
    return () => {
      cancelAnimationFrame(animationFrameId);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      scene.clear();
    };
  }, []);

  const activeColorStr = isListening ? '#ffaa00' : '#00f7ff';

  return (
    <div className="flex flex-col items-center justify-center gap-2 select-none">

      {/* ── Cyber Header Tag ── */}
      <div
        style={{
          fontFamily: 'Orbitron, monospace',
          fontSize: 9,
          letterSpacing: '0.35em',
          color: activeColorStr,
          textShadow: `0 0 10px ${activeColorStr}`,
          textTransform: 'uppercase',
        }}
      >
        MARK-VII · JARVIS 3D NEURAL INTERFACE
      </div>

      {/* ── 3D Canvas Container with Hologram Blueprint Border ── */}
      <div
        className="relative flex items-center justify-center rounded-2xl overflow-hidden"
        style={{
          width: 340,
          height: 380,
          background: 'radial-gradient(circle at center, rgba(0,25,50,0.4) 0%, rgba(2,8,18,0.85) 80%)',
          border: `1px solid ${activeColorStr}33`,
          boxShadow: `0 0 25px ${activeColorStr}22, inset 0 0 40px rgba(0,10,25,0.8)`,
        }}
      >
        {/* Corner Brackets */}
        <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2" style={{ borderColor: activeColorStr }} />
        <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2" style={{ borderColor: activeColorStr }} />
        <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2" style={{ borderColor: activeColorStr }} />
        <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2" style={{ borderColor: activeColorStr }} />

        {/* Blueprint Grid Lines in Background */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage: `linear-gradient(${activeColorStr}22 1px, transparent 1px), linear-gradient(90deg, ${activeColorStr}22 1px, transparent 1px)`,
            backgroundSize: '20px 20px',
          }}
        />

        {/* Three.js Canvas Mount */}
        <div ref={containerRef} className="relative z-10" />

        {/* Status Overlay Badge */}
        <div
          className="absolute bottom-3 font-orbitron text-[9px] tracking-[0.25em] px-3 py-1 rounded-full"
          style={{
            background: 'rgba(0,15,35,0.75)',
            border: `1px solid ${activeColorStr}66`,
            color: activeColorStr,
            textShadow: `0 0 8px ${activeColorStr}`,
          }}
        >
          {isTalking
            ? '◉ JARVIS SPEAKING'
            : isListening
              ? '◎ LISTENING...'
              : wsStatus === 'online'
                ? '◎ SYSTEM ONLINE'
                : '⊘ OFFLINE'}
        </div>
      </div>

      {/* ── Equalizer Waveform Bars ── */}
      <div className="flex items-end justify-center gap-[3px] h-8 mt-1">
        {Array.from({ length: 24 }, (_, i) => (
          <div
            key={i}
            style={{
              width: 3,
              borderRadius: 2,
              backgroundColor: activeColorStr,
              boxShadow: (isTalking || isListening) ? `0 0 8px ${activeColorStr}` : 'none',
              height: (isTalking || isListening) ? `${8 + Math.sin((i + Date.now() * 0.01) * 0.8) * 18 + 4}px` : '4px',
              transition: 'height 0.1s ease',
              opacity: (isTalking || isListening) ? 1 : 0.35,
            }}
          />
        ))}
      </div>

      {/* ── Subtitle Label ── */}
      <div
        style={{
          fontFamily: 'Orbitron, monospace',
          fontSize: 8,
          letterSpacing: '0.3em',
          color: `${activeColorStr}55`,
          textTransform: 'uppercase',
        }}
      >
        ◀ STARK INDUSTRIES · AUTONOMOUS AI ▶
      </div>
    </div>
  );
}
