"use client";

import { useRef, useState } from "react";

import { prefersReducedMotion } from "@/lib/motion";

// The brand motif made large and alive: concentric apertures (ἀλήθεια — "unconcealment")
// with a sweeping evidence beam that reveals a grounded verdict at the centre. The whole
// figure tilts toward the cursor for a subtle parallax. Purely decorative (aria-hidden).

export function HeroAperture() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const frame = useRef(0);

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (prefersReducedMotion()) return;
    if (frame.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    frame.current = requestAnimationFrame(() => {
      setTilt({ x: px, y: py });
      frame.current = 0;
    });
  }

  function reset() {
    setTilt({ x: 0, y: 0 });
  }

  return (
    <div
      aria-hidden
      onMouseMove={onMove}
      onMouseLeave={reset}
      className="relative aspect-square w-full max-w-[420px] [perspective:1200px]"
    >
      <div
        className="h-full w-full transition-transform duration-300 ease-out [transform-style:preserve-3d]"
        style={{
          transform: `rotateY(${tilt.x * 12}deg) rotateX(${-tilt.y * 12}deg)`,
        }}
      >
        <svg viewBox="0 0 400 400" className="h-full w-full overflow-visible">
          <defs>
            <linearGradient id="apertureGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#0d9488" />
              <stop offset="100%" stopColor="#22d3ee" />
            </linearGradient>
            <radialGradient id="apertureGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(34,211,238,0.35)" />
              <stop offset="70%" stopColor="rgba(13,148,136,0.10)" />
              <stop offset="100%" stopColor="rgba(13,148,136,0)" />
            </radialGradient>
            <filter id="apertureBlur" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" />
            </filter>
          </defs>

          {/* Ambient glow */}
          <circle cx="200" cy="200" r="170" fill="url(#apertureGlow)" />

          {/* Sweeping evidence beam */}
          <g className="spin-slow" style={{ transformOrigin: "200px 200px" }}>
            <path
              d="M200 200 L200 24 A176 176 0 0 1 320 96 Z"
              fill="url(#apertureGrad)"
              opacity="0.14"
              filter="url(#apertureBlur)"
            />
          </g>

          {/* Outer dashed aperture ring, rotating slowly */}
          <g className="spin-slow" style={{ transformOrigin: "200px 200px" }}>
            <circle
              cx="200"
              cy="200"
              r="150"
              fill="none"
              stroke="url(#apertureGrad)"
              strokeWidth="2"
              strokeDasharray="44 20"
              strokeLinecap="round"
              opacity="0.85"
            />
          </g>

          {/* Mid ring, counter-rotating */}
          <g className="spin-slower" style={{ transformOrigin: "200px 200px" }}>
            <circle
              cx="200"
              cy="200"
              r="112"
              fill="none"
              stroke="#0d9488"
              strokeWidth="1.5"
              strokeDasharray="8 14"
              opacity="0.5"
            />
          </g>

          {/* Static inner ring */}
          <circle
            cx="200"
            cy="200"
            r="78"
            fill="rgba(255,255,255,0.5)"
            stroke="rgba(13,148,136,0.35)"
            strokeWidth="1.5"
          />

          {/* Centre: a grounded verdict revealed */}
          <g style={{ transform: `translate(${tilt.x * 10}px, ${tilt.y * 10}px)` }}>
            <circle cx="200" cy="200" r="8" fill="url(#apertureGrad)" />
            <path
              d="M182 200 l12 12 l24 -26"
              fill="none"
              stroke="#0d9488"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>

          {/* Orbiting evidence node */}
          <g className="spin-slow" style={{ transformOrigin: "200px 200px" }}>
            <circle cx="350" cy="200" r="5" fill="#22d3ee">
              <animate
                attributeName="opacity"
                values="0.4;1;0.4"
                dur="2.4s"
                repeatCount="indefinite"
              />
            </circle>
          </g>
        </svg>
      </div>
    </div>
  );
}
