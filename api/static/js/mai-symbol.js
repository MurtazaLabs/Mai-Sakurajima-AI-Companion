<!--
  MAI Visual Identity Symbol - 3 Orbital Lines Forming "M"
  A geometric symbol representing MAI's orbital intelligence
  
  Usage:
  <mai-symbol size="48" animated="true"></mai-symbol>
  
  Attributes:
  - size: number (default: 48) - Size in pixels
  - animated: boolean (default: false) - Enable orbital animation
  - variant: string (default: 'primary') - 'primary' | 'secondary' | 'outline' | 'mono'
  - speed: number (default: 1) - Animation speed multiplier
-->

<template id="mai-symbol-template">
  <svg class="mai-symbol" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" role="img" aria-label="MAI">
    <title>MAI</title>
    <defs>
      <!-- Gradient for orbital lines -->
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
      
      <!-- Glow filter -->
      <filter id="mai-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      
      <!-- Soft glow filter -->
      <filter id="mai-soft-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    
    <!-- Orbital Ring 1 (Outer) - Forms left diagonal of M -->
    <g class="orbital-ring orbital-ring-1" filter="url(#mai-soft-glow)">
      <path 
        class="orbital-path" 
        d="M 15 85 Q 50 15 85 85" 
        fill="none" 
        stroke="url(#mai-gradient-primary)" 
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-dasharray="0 0"
      />
      <!-- Orbital node -->
      <circle 
        class="orbital-node" 
        cx="50" 
        cy="50" 
        r="4" 
        fill="#7C5CFF" 
        opacity="0.8"
      />
    </g>
    
    <!-- Orbital Ring 2 (Middle) - Forms center peak of M -->
    <g class="orbital-ring orbital-ring-2" filter="url(#mai-glow)">
      <path 
        class="orbital-path" 
        d="M 25 85 Q 50 25 75 85" 
        fill="none" 
        stroke="url(#mai-gradient-secondary)" 
        stroke-width="2"
        stroke-linecap="round"
        stroke-dasharray="0 0"
      />
      <!-- Orbital nodes -->
      <circle 
        class="orbital-node orbital-node-left" 
        cx="35" 
        cy="55" 
        r="3" 
        fill="#9B86FF" 
        opacity="0.9"
      />
      <circle 
        class="orbital-node orbital-node-right" 
        cx="65" 
        cy="55" 
        r="3" 
        fill="#6EA8FF" 
        opacity="0.9"
      />
    </g>
    
    <!-- Orbital Ring 3 (Inner) - Forms right diagonal of M -->
    <g class="orbital-ring orbital-ring-3" filter="url(#mai-soft-glow)">
      <path 
        class="orbital-path" 
        d="M 35 85 Q 50 35 65 85" 
        fill="none" 
        stroke="url(#mai-gradient-primary)" 
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-dasharray="0 0"
      />
      <!-- Central core -->
      <circle 
        class="orbital-core" 
        cx="50" 
        cy="50" 
        r="6" 
        fill="url(#mai-gradient-glow)" 
        opacity="0.4"
      />
      <circle 
        class="orbital-core-inner" 
        cx="50" 
        cy="50" 
        r="3" 
        fill="#FFFFFF" 
        opacity="0.9"
      />
    </g>
    
    <!-- Particle system (for animated variant) -->
    <g class="orbital-particles" style="display: none;">
      <!-- Particles will be added dynamically via JS -->
    </g>
  </svg>
</template>

<script>
/**
 * MAI Symbol Web Component
 * Self-contained custom element for the MAI visual identity
 */
class MAISymbol extends HTMLElement {
  static get observedAttributes() {
    return ['size', 'animated', 'variant', 'speed'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._animationId = null;
    this._particles = [];
    this._lastFrame = 0;
  }

  connectedCallback() {
    this.render();
    this.setupAnimation();
  }

  disconnectedCallback() {
    this.stopAnimation();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.render();
      this.setupAnimation();
    }
  }

  get size() {
    return parseInt(this.getAttribute('size')) || 48;
  }

  get animated() {
    return this.hasAttribute('animated');
  }

  get variant() {
    return this.getAttribute('variant') || 'primary';
  }

  get speed() {
    return parseFloat(this.getAttribute('speed')) || 1;
  }

  render() {
    const template = document.getElementById('mai-symbol-template');
    if (!template) {
      console.warn('MAI Symbol template not found');
      return;
    }

    const clone = template.content.cloneNode(true);
    const svg = clone.querySelector('.mai-symbol');
    
    // Set size
    svg.style.width = `${this.size}px`;
    svg.style.height = `${this.size}px`;
    
    // Apply variant styles
    this.applyVariant(clone);
    
    // Apply animation styles if animated
    if (this.animated) {
      this.applyAnimationStyles(clone);
    }
    
    // Clear shadow DOM and append
    this.shadowRoot.innerHTML = '';
    this.shadowRoot.appendChild(clone);
    
    // Inject styles
    this.injectStyles();
  }

  applyVariant(clone) {
    const svg = clone.querySelector('.mai-symbol');
    const paths = clone.querySelectorAll('.orbital-path');
    const nodes = clone.querySelectorAll('.orbital-node');
    const cores = clone.querySelectorAll('.orbital-core, .orbital-core-inner');
    
    switch (this.variant) {
      case 'secondary':
        paths.forEach(p => p.setAttribute('stroke', '#6EA8FF'));
        nodes.forEach(n => n.setAttribute('fill', '#6EA8FF'));
        break;
      case 'outline':
        paths.forEach(p => {
          p.setAttribute('stroke', '#FFFFFF');
          p.setAttribute('stroke-width', parseFloat(p.getAttribute('stroke-width')) * 0.8);
        });
        nodes.forEach(n => n.setAttribute('fill', '#FFFFFF'));
        cores.forEach(c => c.setAttribute('fill', 'none'));
        break;
      case 'mono':
        paths.forEach(p => p.setAttribute('stroke', '#FFFFFF'));
        nodes.forEach(n => n.setAttribute('fill', '#FFFFFF'));
        cores.forEach(c => c.setAttribute('fill', '#FFFFFF'));
        break;
      case 'primary':
      default:
        // Use gradient defaults from template
        break;
    }
  }

  applyAnimationStyles(clone) {
    const style = document.createElement('style');
    style.textContent = `
      .orbital-ring-1 { animation: orbital-rotate ${20 / this.speed}s linear infinite; }
      .orbital-ring-2 { animation: orbital-rotate ${30 / this.speed}s linear infinite reverse; }
      .orbital-ring-3 { animation: orbital-rotate ${40 / this.speed}s linear infinite; }
      .orbital-node { animation: breathing ${4 / this.speed}s ease-in-out infinite; }
      .orbital-core { animation: pulse-glow ${2 / this.speed}s ease-in-out infinite; }
      .orbital-core-inner { animation: breathing ${3 / this.speed}s ease-in-out infinite; }
      
      @keyframes orbital-rotate {
        from { transform: rotate(0deg); transform-origin: 50px 50px; }
        to { transform: rotate(360deg); transform-origin: 50px 50px; }
      }
      
      @keyframes breathing {
        0%, 100% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.15); opacity: 1; }
      }
      
      @keyframes pulse-glow {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.6; }
      }
    `;
    clone.appendChild(style);
  }

  injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      :host {
        display: inline-block;
        line-height: 1;
      }
      
      .mai-symbol {
        display: block;
        width: 100%;
        height: 100%;
      }
      
      .orbital-ring {
        transform-origin: 50px 50px;
      }
      
      .orbital-path {
        transition: stroke-width 0.3s ease, opacity 0.3s ease;
      }
      
      .orbital-node {
        transform-origin: center;
        transition: fill 0.3s ease, opacity 0.3s ease;
      }
      
      .orbital-core {
        transform-origin: center;
      }
      
      .orbital-core-inner {
        transform-origin: center;
      }
      
      /* Reduced motion */
      @media (prefers-reduced-motion: reduce) {
        .orbital-ring,
        .orbital-node,
        .orbital-core,
        .orbital-core-inner {
          animation: none !important;
        }
        .orbital-ring {
          transform: none !important;
        }
      }
      
      /* Hover effect for interactive use */
      :host(:hover) .orbital-path {
        stroke-width: calc(var(--stroke-width, 2) * 1.2);
      }
      
      :host(:hover) .orbital-node {
        transform: scale(1.2);
      }
      
      :host(:hover) .orbital-core {
        opacity: 0.6;
      }
      
      :host(:hover) .orbital-core-inner {
        transform: scale(1.1);
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  setupAnimation() {
    if (!this.animated) {
      this.stopAnimation();
      return;
    }

    // Check reduced motion preference
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    this.startParticleSystem();
  }

  startParticleSystem() {
    const particlesContainer = this.shadowRoot.querySelector('.orbital-particles');
    if (!particlesContainer) return;

    particlesContainer.style.display = 'block';
    this._particles = [];
    
    // Create particles
    for (let i = 0; i < 12; i++) {
      const particle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      particle.setAttribute('r', Math.random() * 1.5 + 0.5);
      particle.setAttribute('fill', ['#7C5CFF', '#9B86FF', '#6EA8FF'][Math.floor(Math.random() * 3)]);
      particle.setAttribute('opacity', '0');
      particle.setAttribute('class', 'orbital-particle');
      particlesContainer.appendChild(particle);
      
      this._particles.push({
        element: particle,
        angle: Math.random() * Math.PI * 2,
        radius: 30 + Math.random() * 20,
        speed: (0.5 + Math.random() * 1.5) * this.speed,
        phase: Math.random() * Math.PI * 2,
        life: 0,
        maxLife: 2 + Math.random() * 3
      });
    }

    this.animateParticles();
  }

  animateParticles() {
    const animate = (timestamp) => {
      if (!this._animationId) return;
      
      const delta = (timestamp - this._lastFrame) / 1000;
      this._lastFrame = timestamp;
      
      this._particles.forEach((particle, index) => {
        particle.life += delta;
        
        if (particle.life >= particle.maxLife) {
          // Reset particle
          particle.life = 0;
          particle.angle = Math.random() * Math.PI * 2;
          particle.radius = 30 + Math.random() * 20;
          particle.phase = Math.random() * Math.PI * 2;
          particle.element.setAttribute('opacity', '0');
        } else {
          // Update position
          particle.angle += particle.speed * delta * 0.5;
          
          const x = 50 + Math.cos(particle.angle) * particle.radius;
          const y = 50 + Math.sin(particle.angle) * particle.radius;
          
          // Fade in/out based on life
          const progress = particle.life / particle.maxLife;
          let opacity = 0;
          if (progress < 0.2) {
            opacity = progress / 0.2;
          } else if (progress > 0.8) {
            opacity = (1 - progress) / 0.2;
          } else {
            opacity = 1;
          }
          
          particle.element.setAttribute('cx', x);
          particle.element.setAttribute('cy', y);
          particle.element.setAttribute('opacity', opacity * 0.7);
        }
      });
      
      this._animationId = requestAnimationFrame(animate);
    };
    
    this._animationId = requestAnimationFrame(animate);
  }

  stopAnimation() {
    if (this._animationId) {
      cancelAnimationFrame(this._animationId);
      this._animationId = null;
    }
    
    const particlesContainer = this.shadowRoot?.querySelector('.orbital-particles');
    if (particlesContainer) {
      particlesContainer.innerHTML = '';
      particlesContainer.style.display = 'none';
    }
    this._particles = [];
  }
}

// Register custom element
if (!customElements.get('mai-symbol')) {
  customElements.define('mai-symbol', MAISymbol);
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MAISymbol;
}
</script>

<style>
/* Fallback styles for when Web Components not supported */
.mai-symbol-fallback {
  display: inline-block;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #7C5CFF, #9B86FF, #6EA8FF);
  border-radius: 50%;
  mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M15 85 Q50 15 85 85 M25 85 Q50 25 75 85 M35 85 Q50 35 65 85' fill='none' stroke='white' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E");
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M15 85 Q50 15 85 85 M25 85 Q50 25 75 85 M35 85 Q50 35 65 85' fill='none' stroke='white' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E");
}
</style>