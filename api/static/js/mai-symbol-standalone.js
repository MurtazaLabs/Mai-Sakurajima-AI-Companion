/**
 * MAI Symbol - Standalone CSS/HTML Component
 * Can be used directly in HTML without React or Web Components
 * 
 * Usage:
 * <div class="mai-symbol" data-size="48" data-animated="true"></div>
 * <script src="mai-symbol-standalone.js"></script>
 */

// ============================================================================
// CSS STYLES (inject via <style> or include in CSS bundle)
// ============================================================================

export const maiSymbolStyles = `
.mai-symbol {
  display: inline-block;
  line-height: 1;
  width: 48px;
  height: 48px;
  --size: 48px;
}

.mai-symbol svg {
  display: block;
  width: 100%;
  height: 100%;
}

.mai-symbol .orbital-ring {
  transform-origin: 50px 50px;
}

.mai-symbol .orbital-path {
  transition: stroke-width 0.3s ease, opacity 0.3s ease;
}

.mai-symbol .orbital-node {
  transform-origin: center;
  transition: fill 0.3s ease, opacity 0.3s ease;
}

.mai-symbol .orbital-core,
.mai-symbol .orbital-core-inner {
  transform-origin: center;
}

/* Animations */
.mai-symbol.animated .orbital-ring-1 {
  animation: mai-orbital-rotate 20s linear infinite;
}

.mai-symbol.animated .orbital-ring-2 {
  animation: mai-orbital-rotate 30s linear infinite reverse;
}

.mai-symbol.animated .orbital-ring-3 {
  animation: mai-orbital-rotate 40s linear infinite;
}

.mai-symbol.animated .orbital-node {
  animation: mai-breathing 4s ease-in-out infinite;
}

.mai-symbol.animated .orbital-core {
  animation: mai-pulse-glow 2s ease-in-out infinite;
}

.mai-symbol.animated .orbital-core-inner {
  animation: mai-breathing 3s ease-in-out infinite;
}

@keyframes mai-orbital-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes mai-breathing {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
}

@keyframes mai-pulse-glow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

/* Variants */
.mai-symbol.variant-secondary .orbital-path { stroke: #6EA8FF; }
.mai-symbol.variant-secondary .orbital-node { fill: #6EA8FF; }

.mai-symbol.variant-outline .orbital-path { 
  stroke: #FFFFFF; 
  stroke-width: 2;
}
.mai-symbol.variant-outline .orbital-node { fill: #FFFFFF; }
.mai-symbol.variant-outline .orbital-core { fill: none; }

.mai-symbol.variant-mono .orbital-path { stroke: #FFFFFF; }
.mai-symbol.variant-mono .orbital-node { fill: #FFFFFF; }
.mai-symbol.variant-mono .orbital-core { fill: #FFFFFF; }

/* Hover effects */
.mai-symbol:hover .orbital-path {
  stroke-width: calc(var(--stroke-width, 2) * 1.2);
}

.mai-symbol:hover .orbital-node {
  transform: scale(1.2);
}

.mai-symbol:hover .orbital-core {
  opacity: 0.6;
}

.mai-symbol:hover .orbital-core-inner {
  transform: scale(1.1);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .mai-symbol.animated .orbital-ring,
  .mai-symbol.animated .orbital-node,
  .mai-symbol.animated .orbital-core,
  .mai-symbol.animated .orbital-core-inner {
    animation: none !important;
  }
  .mai-symbol.animated .orbital-ring {
    transform: none !important;
  }
}

/* Size variants */
.mai-symbol.size-xs { width: 24px; height: 24px; }
.mai-symbol.size-sm { width: 32px; height: 32px; }
.mai-symbol.size-md { width: 48px; height: 48px; }
.mai-symbol.size-lg { width: 64px; height: 64px; }
.mai-symbol.size-xl { width: 96px; height: 96px; }
`;

// ============================================================================
// SVG TEMPLATE
// ============================================================================

export const maiSymbolSVG = (options: {
  size?: number;
  animated?: boolean;
  variant?: 'primary' | 'secondary' | 'outline' | 'mono';
  speed?: number;
} = {}) => {
  const { size = 48, animated = false, variant = 'primary', speed = 1 } = options;
  
  const gradients = {
    primary: {
      ring1: 'url(#mai-gradient-primary)',
      ring2: 'url(#mai-gradient-secondary)',
      ring3: 'url(#mai-gradient-primary)',
      node1: '#7C5CFF',
      node2Left: '#9B86FF',
      node2Right: '#6EA8FF',
      core: 'url(#mai-gradient-glow)',
      coreInner: '#FFFFFF'
    },
    secondary: {
      ring1: '#6EA8FF',
      ring2: '#6EA8FF',
      ring3: '#6EA8FF',
      node1: '#6EA8FF',
      node2Left: '#6EA8FF',
      node2Right: '#6EA8FF',
      core: '#6EA8FF',
      coreInner: '#FFFFFF'
    },
    outline: {
      ring1: '#FFFFFF',
      ring2: '#FFFFFF',
      ring3: '#FFFFFF',
      node1: '#FFFFFF',
      node2Left: '#FFFFFF',
      node2Right: '#FFFFFF',
      core: 'none',
      coreInner: '#FFFFFF'
    },
    mono: {
      ring1: '#FFFFFF',
      ring2: '#FFFFFF',
      ring3: '#FFFFFF',
      node1: '#FFFFFF',
      node2Left: '#FFFFFF',
      node2Right: '#FFFFFF',
      core: '#FFFFFF',
      coreInner: '#FFFFFF'
    }
  };

  const colors = gradients[variant];
  const ringPaths = {
    ring1: 'M 15 85 Q 50 15 85 85',
    ring2: 'M 25 85 Q 50 25 75 85',
    ring3: 'M 35 85 Q 50 35 65 85'
  };
  const ringStrokeWidths = { ring1: 2.5, ring2: 2, ring3: 1.5 };

  const animationStyles = animated ? `
    .orbital-ring-1 { animation: mai-orbital-rotate ${20 / speed}s linear infinite; }
    .orbital-ring-2 { animation: mai-orbital-rotate ${30 / speed}s linear infinite reverse; }
    .orbital-ring-3 { animation: mai-orbital-rotate ${40 / speed}s linear infinite; }
    .orbital-node { animation: mai-breathing ${4 / speed}s ease-in-out infinite; }
    .orbital-core { animation: mai-pulse-glow ${2 / speed}s ease-in-out infinite; }
    .orbital-core-inner { animation: mai-breathing ${3 / speed}s ease-in-out infinite; }
  ` : '';

  return `
<svg class="mai-symbol-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" width="${size}" height="${size}" role="img" aria-label="MAI">
  <title>MAI</title>
  <defs>
    <linearGradient id="mai-gradient-primary" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C5CFF" stop-opacity="1"/>
      <stop offset="50%" stop-color="#9B86FF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#6EA8FF" stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="mai-gradient-secondary" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#6EA8FF" stop-opacity="1"/>
      <stop offset="50%" stop-color="#7C5CFF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#9B86FF" stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="mai-gradient-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C5CFF" stop-opacity="0.3"/>
      <stop offset="50%" stop-color="#9B86FF" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#6EA8FF" stop-opacity="0.3"/>
    </linearGradient>
    <filter id="mai-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="mai-soft-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      @keyframes mai-orbital-rotate {
        from { transform: rotate(0deg); transform-origin: 50px 50px; }
        to { transform: rotate(360deg); transform-origin: 50px 50px; }
      }
      @keyframes mai-breathing {
        0%, 100% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.15); opacity: 1; }
      }
      @keyframes mai-pulse-glow {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.6; }
      }
      @media (prefers-reduced-motion: reduce) {
        .orbital-ring, .orbital-node, .orbital-core, .orbital-core-inner { animation: none !important; }
        .orbital-ring { transform: none !important; }
      }
      ${animationStyles}
    </style>
  </defs>
  
  <g class="orbital-ring orbital-ring-1" filter="url(#mai-soft-glow)">
    <path class="orbital-path" d="${ringPaths.ring1}" fill="none" stroke="${colors.ring1}" stroke-width="${ringStrokeWidths.ring1}" stroke-linecap="round"/>
    <circle class="orbital-node" cx="50" cy="50" r="4" fill="${colors.node1}" opacity="0.8"/>
  </g>
  
  <g class="orbital-ring orbital-ring-2" filter="url(#mai-glow)">
    <path class="orbital-path" d="${ringPaths.ring2}" fill="none" stroke="${colors.ring2}" stroke-width="${ringStrokeWidths.ring2}" stroke-linecap="round"/>
    <circle class="orbital-node orbital-node-left" cx="35" cy="55" r="3" fill="${colors.node2Left}" opacity="0.9"/>
    <circle class="orbital-node orbital-node-right" cx="65" cy="55" r="3" fill="${colors.node2Right}" opacity="0.9"/>
  </g>
  
  <g class="orbital-ring orbital-ring-3" filter="url(#mai-soft-glow)">
    <path class="orbital-path" d="${ringPaths.ring3}" fill="none" stroke="${colors.ring3}" stroke-width="${ringStrokeWidths.ring3}" stroke-linecap="round"/>
    <circle class="orbital-core" cx="50" cy="50" r="6" fill="${colors.core}" opacity="0.4"/>
    <circle class="orbital-core-inner" cx="50" cy="50" r="3" fill="${colors.coreInner}" opacity="0.9"/>
  </g>
  
  ${animated ? '<g class="orbital-particles"></g>' : ''}
</svg>
  `;
};

// ============================================================================
// AUTO-INITIALIZATION FOR HTML
// ============================================================================

if (typeof window !== 'undefined') {
  // Auto-initialize elements with data-mai-symbol attribute
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-symbol]').forEach(el => {
      const size = parseInt(el.getAttribute('data-size') || '48');
      const animated = el.hasAttribute('data-animated');
      const variant = el.getAttribute('data-variant') || 'primary';
      const speed = parseFloat(el.getAttribute('data-speed') || '1');
      
      el.innerHTML = maiSymbolSVG({ size, animated, variant, speed });
      el.classList.add('mai-symbol');
      if (animated) el.classList.add('animated');
      if (variant !== 'primary') el.classList.add(`variant-${variant}`);
      el.classList.add(`size-${size <= 24 ? 'xs' : size <= 32 ? 'sm' : size <= 48 ? 'md' : size <= 64 ? 'lg' : 'xl'}`);
    });
  });
}

export default { maiSymbolStyles, maiSymbolSVG };