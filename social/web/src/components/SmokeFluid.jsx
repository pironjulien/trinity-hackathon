import React, { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const ParticleShader = {
    uniforms: {
        uTime: { value: 0 },
        uMouse: { value: new THREE.Vector3(0, 0, 0) },
        uPixelRatio: { value: 1 }
    },
    vertexShader: `
    uniform float uTime;
    uniform vec3 uMouse;
    uniform float uPixelRatio;
    
    attribute float aScale;
    attribute vec3 aVelocity;
    
    varying float vAlpha;

    void main() {
      vec3 pos = position;
      
      // Basic movement (Flow)
      pos.x += sin(uTime * 0.1 + pos.y * 0.5) * 0.2;
      pos.y += uTime * 0.2;
      
      // Loop y position
      if (pos.y > 10.0) pos.y -= 20.0;
      
      // Interactive Repulsion
      // Calculate distance to mouse in world space (roughly mapped)
      // We assume mouse Z is 0, particles are around Z=0
      float dist = distance(pos.xy, uMouse.xy);
      float repulsion = smoothstep(3.0, 0.0, dist);
      
      // Push away from mouse
      vec3 dir = normalize(pos - vec3(uMouse.xy, 0.0));
      pos += dir * repulsion * 2.0;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      
      // Size attenuation based on depth
      gl_PointSize = aScale * uPixelRatio * (50.0 / -mvPosition.z);
      
      // Fade out based on repulsion (holes) or depth
      vAlpha = 0.6 * (1.0 - repulsion); 
    }
  `,
    fragmentShader: `
    varying float vAlpha;
    
    void main() {
      // Soft circular particle
      vec2 center = gl_PointCoord - 0.5;
      float dist = length(center);
      if (dist > 0.5) discard;
      
      // Soft edge glow
      float glow = 1.0 - (dist * 2.0);
      glow = pow(glow, 1.5);
      
      vec3 color = vec3(0.6, 0.8, 1.0); // Light blueish smoke
      
      gl_FragColor = vec4(color, vAlpha * glow * 0.3); // Low opacity for smoke feel
    }
  `
};

const SmokeFluid = ({ count = 8000 }) => {
    const meshRef = useRef();
    const { viewport, mouse, size } = useThree();
    const mouseRef = useRef(new THREE.Vector3(0, 0, 0));

    // Generate particles
    const particles = useMemo(() => {
        const temp = [];
        const positions = new Float32Array(count * 3);
        const scales = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            // Random positions in a volume
            positions[i * 3] = (Math.random() - 0.5) * 25;     // x
            positions[i * 3 + 1] = (Math.random() - 0.5) * 20; // y
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10; // z

            scales[i] = Math.random();
        }
        return { positions, scales };
    }, [count]);

    const shaderMaterial = useMemo(() => {
        return new THREE.ShaderMaterial({
            uniforms: THREE.UniformsUtils.clone(ParticleShader.uniforms),
            vertexShader: ParticleShader.vertexShader,
            fragmentShader: ParticleShader.fragmentShader,
            transparent: true,
            depthWrite: false, // Smoke shouldn't occlude itself rigorously
            blending: THREE.AdditiveBlending
        });
    }, []);

    useFrame((state) => {
        if (meshRef.current) {
            meshRef.current.material.uniforms.uTime.value = state.clock.elapsedTime;
            meshRef.current.material.uniforms.uPixelRatio.value = state.gl.getPixelRatio();

            // Map normalized mouse (-1..1) to world coordinates rough approximation depends on camera
            // Camera is usually at z=5 or z=10.
            // Or unproject. For simple visual effect, scaling is enough.
            const x = (state.pointer.x * viewport.width) / 2;
            const y = (state.pointer.y * viewport.height) / 2;

            // Smooth lerp
            mouseRef.current.lerp(new THREE.Vector3(x, y, 0), 0.1);
            meshRef.current.material.uniforms.uMouse.value.copy(mouseRef.current);
        }
    });

    return (
        <points ref={meshRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={particles.positions.length / 3}
                    array={particles.positions}
                    itemSize={3}
                />
                <bufferAttribute
                    attach="attributes-aScale"
                    count={particles.scales.length}
                    array={particles.scales}
                    itemSize={1}
                />
            </bufferGeometry>
            <primitive object={shaderMaterial} attach="material" />
        </points>
    );
};

export default SmokeFluid;
