import { useEffect } from 'react';

/**
 * Metal/Hole Effect Calculators
 */
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

function bottomRoundedPath(w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    return `M0,0 H${w} V${h - r} A${r},${r} 0 0 1 ${w - r},${h} H${r} A${r},${r} 0 0 1 0,${h - r} Z`;
}

function topRoundedPath(w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    return `M${r},0 H${w - r} A${r},${r} 0 0 1 ${w},${r} V${h} H0 V${r} A${r},${r} 0 0 1 ${r},0 Z`;
}

function makeMetalDual({ width, height, radius = 14, holeX1, holeR1, holeX2, holeR2, topHoles = false }) {
    const rMax = Math.max(holeR1, holeR2);
    const overshoot = Math.max(1, Math.round(rMax * 0.08));
    const cy = topHoles ? -overshoot : height + overshoot;

    // Card-style Glass Theme
    const glassColor = "rgba(18, 18, 30, 0.3)";

    const path = topHoles
        ? topRoundedPath(width, height, radius)
        : bottomRoundedPath(width, height, radius);

    const topHLH = clamp(Math.round(height * 0.12), 6, 12);

    // Light reflection overlays
    const overlays = `
      <linearGradient id="topHL" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%"   stop-color="${topHoles ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0)"}"/>
        <stop offset="100%" stop-color="${topHoles ? "rgba(255,255,255,0)" : "rgba(255,255,255,0.25)"}"/>
      </linearGradient>
    `;

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
  <defs>
    ${overlays}
    <mask id="cut">
      <path d="${path}" fill="#fff"/>
      <circle cx="${holeX1}" cy="${cy}" r="${holeR1}" fill="#000"/>
      <circle cx="${holeX2}" cy="${cy}" r="${holeR2}" fill="#000"/>
    </mask>
  </defs>
  <rect x="0" y="0" width="${width}" height="${height}" fill="${glassColor}" mask="url(#cut)"/>
  <rect x="0" y="${topHoles ? 0 : height - topHLH}" width="${width}" height="${topHLH}" fill="url(#topHL)" mask="url(#cut)"/>
</svg>`.trim();

    return `url('data:image/svg+xml;utf8,${encodeURIComponent(svg)}')`;
}

function makeMetalMask({ width, height, radius = 14, holeX1, holeR1, holeX2, holeR2, topHoles = false }) {
    const rMax = Math.max(holeR1, holeR2);
    const overshoot = Math.max(1, Math.round(rMax * 0.08));
    const cy = topHoles ? -overshoot : height + overshoot;

    const path = topHoles
        ? topRoundedPath(width, height, radius)
        : bottomRoundedPath(width, height, radius);

    // Mask Logic: White = Visible, Black = Hidden (Holes)
    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
  <defs>
    <mask id="mask_cut">
      <path d="${path}" fill="#fff"/>
      <circle cx="${holeX1}" cy="${cy}" r="${holeR1}" fill="#000"/>
      <circle cx="${holeX2}" cy="${cy}" r="${holeR2}" fill="#000"/>
    </mask>
  </defs>
  <rect x="0" y="0" width="${width}" height="${height}" fill="#fff" mask="url(#mask_cut)"/>
</svg>`.trim();

    return `url('data:image/svg+xml;utf8,${encodeURIComponent(svg)}')`;
}

function holeFrom(container, logo) {
    if (!container || !logo) return { x: 0, r: 0 };
    const c = container.getBoundingClientRect();
    const l = logo.getBoundingClientRect();
    // Assuming root CSS variables are available on document element
    const cssGap = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--julien-chrome-gap")) || 8;
    const x = l.left + l.width / 2 - c.left;
    const r = Math.max(0, Math.max(l.width, l.height) / 2 + cssGap);
    return { x: Math.round(x), r: Math.round(r) };
}

/**
 * Hook to apply the metal bar effect
 * @param {React.RefObject} containerRef 
 * @param {React.RefObject} logo1Ref 
 * @param {React.RefObject} logo2Ref 
 * @param {boolean} topHoles - If true, holes are at the top (for menu), otherwise bottom (header)
 * @param {Array<React.RefObject>} additionalRefs - Extra elements to observe for resize (e.g. grid columns)
 */
export function useMetalBar(containerRef, logo1Ref, logo2Ref, topHoles = false, additionalRefs = []) {
    useEffect(() => {
        const updateBars = () => {
            const container = containerRef.current;
            const logo1 = logo1Ref?.current;
            const logo2 = logo2Ref?.current;

            if (!container) return;

            const { width, height } = container.getBoundingClientRect();

            // Calculate holes
            const h1 = holeFrom(container, logo1);
            const h2 = holeFrom(container, logo2);

            // Calculate overshoot CSS variable if main header
            if (!topHoles && (h1.r > 0 || h2.r > 0)) {
                const rMax = Math.max(h1.r, h2.r);
                const overshoot = Math.max(1, Math.round(rMax * 0.08));
                document.documentElement.style.setProperty("--julien-hole-overshoot", overshoot + "px");
            }

            const params = {
                width: Math.round(width),
                height: Math.round(height),
                radius: 13, // --julien-radius
                holeX1: h1.x,
                holeR1: h1.r,
                holeX2: h2.x,
                holeR2: h2.r,
                topHoles,
            };

            // 1. Visual Texture (Glass + Highlights)
            container.style.backgroundImage = makeMetalDual(params);
            container.style.backgroundSize = "100% 100%";

            // 2. Shape Mask (For Blur Clipping)
            const maskUri = makeMetalMask(params);
            container.style.maskImage = maskUri;
            container.style.webkitMaskImage = maskUri;
            container.style.maskSize = "100% 100%";
            container.style.webkitMaskSize = "100% 100%";

            // 3. Apply Blur (Now safely clipped)
            // SOTA: Apply blur via backdrop-filter, constrained by the mask
            container.style.backdropFilter = "blur(20px)";
            container.style.webkitBackdropFilter = "blur(20px)";
        };

        const scheduleUpdateBars = (() => {
            let scheduled = false;
            return () => {
                if (scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => {
                    scheduled = false;
                    updateBars();
                });
            };
        })();

        // Initial update
        scheduleUpdateBars();
        // Safety net for font loading/layout shifts
        setTimeout(scheduleUpdateBars, 300);

        // Listen for resize
        window.addEventListener("resize", scheduleUpdateBars);

        // Resize Observer
        let observer;
        if ("ResizeObserver" in window) {
            observer = new ResizeObserver(() => scheduleUpdateBars());
            if (containerRef.current) observer.observe(containerRef.current);
            if (logo1Ref?.current) observer.observe(logo1Ref.current);
            if (logo2Ref?.current) observer.observe(logo2Ref.current);

            // Observe additional structural elements
            additionalRefs.forEach(ref => {
                if (ref?.current) observer.observe(ref.current);
            });
        }

        // Image load listeners
        const logo1Img = logo1Ref?.current;
        const logo2Img = logo2Ref?.current;

        if (logo1Img) logo1Img.addEventListener('load', scheduleUpdateBars);
        if (logo2Img) logo2Img.addEventListener('load', scheduleUpdateBars);

        return () => {
            window.removeEventListener("resize", scheduleUpdateBars);
            if (observer) observer.disconnect();
            if (logo1Img) logo1Img.removeEventListener('load', scheduleUpdateBars);
            if (logo2Img) logo2Img.removeEventListener('load', scheduleUpdateBars);
        };
    }, [containerRef, logo1Ref, logo2Ref, topHoles, ...additionalRefs]); // Add vars to dependency array
}
