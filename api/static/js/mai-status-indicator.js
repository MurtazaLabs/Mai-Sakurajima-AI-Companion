/**
 * MAI Status Indicator - 8 State Visual Indicator
 * Shows MAI's current cognitive/voice state with distinct animations
 * 
 * States: idle, listening, thinking, speaking, processing, sleeping, updating, offline
 * 
 * Usage:
 * import { MAIStatusIndicator } from './mai-status-indicator.js';
 * const indicator = new MAIStatusIndicator({ container: '#status', size: 'md' });
 * indicator.setState('listening');
 */

// ============================================================================
// STATE CONFIGURATION
// ============================================================================

const STATE_CONFIG = {
  idle: {
    label: 'IDLE',
    color: '#7C5CFF',
    ariaLabel: 'MAI is idle, ready for input',
    animation: 'pulse'
  },
  listening: {
    label: 'LISTENING',
    color: '#6EA8FF',
    ariaLabel: 'MAI is listening to voice input',
    animation: 'waveform'
  },
  thinking: {
    label: 'THINKING',
    color: '#9B86FF',
    ariaLabel: 'MAI is processing thoughts',
    animation: 'dots'
  },
  speaking: {
    label: 'SPEAKING',
    color: '#72D6A5',
    ariaLabel: 'MAI is speaking',
    animation: 'rings'
  },
  processing: {
    label: 'PROCESSING',
    color: '#E8B86A',
    ariaLabel: 'MAI is processing a request',
    animation: 'spin'
  },
  sleeping: {
    label: 'SLEEPING',
    color: '#7C5CFF',
    ariaLabel: 'MAI is in sleep mode',
    animation: 'slow-pulse'
  },
  updating: {
    label: 'UPDATING',
    color: '#6EA8FF',
    ariaLabel: 'MAI is updating',
    animation: 'dual-spin'
  },
  offline: {
    label: 'OFFLINE',
    color: '#6E7785',
    ariaLabel: 'MAI is offline',
    animation: 'none'
  }
};

const SIZE_CONFIG = {
  xs: { dot: 6, label: '10px', padding: '2px 6px', gap: '4px' },
  sm: { dot: 8, label: '11px', padding: '3px 8px', gap: '6px' },
  md: { dot: 10, label: '12px', padding: '4px 10px', gap: '8px' },
  lg: { dot: 12, label: '13px', padding: '5px 12px', gap: '10px' }
};

// ============================================================================
// CSS STYLES (injected once)
// ============================================================================

const STYLES = `
.mai-status-indicator {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-radius: 9999px;
  white-space: nowrap;
  transition: all 250ms ease-out;
  user-select: none;
}

.mai-status-indicator__dot {
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  transition: all 250ms ease-out;
}

.mai-status-indicator__label {
  display: none;
}

.mai-status-indicator--with-label .mai-status-indicator__label {
  display: inline-block;
}

/* Sizes */
.mai-status-indicator--xs .mai-status-indicator__dot { width: 6px; height: 6px; }
.mai-status-indicator--sm .mai-status-indicator__dot { width: 8px; height: 8px; }
.mai-status-indicator--md .mai-status-indicator__dot { width: 10px; height: 10px; }
.mai-status-indicator--lg .mai-status-indicator__dot { width: 12px; height: 12px; }

.mai-status-indicator--xs { font-size: 10px; padding: 2px 6px; gap: 4px; }
.mai-status-indicator--sm { font-size: 11px; padding: 3px 8px; gap: 6px; }
.mai-status-indicator--md { font-size: 12px; padding: 4px 10px; gap: 8px; }
.mai-status-indicator--lg { font-size: 13px; padding: 5px 12px; gap: 10px; }

/* Animations */

/* Pulse - for idle state */
@keyframes mai-pulse {
  0%, 100% { 
    box-shadow: 0 0 8px currentColor; 
    opacity: 1; 
  }
  50% { 
    box-shadow: 0 0 20px currentColor, 0 0 32px currentColor; 
    opacity: 0.8; 
  }
}

/* Slow pulse - for sleeping */
@keyframes mai-slow-pulse {
  0%, 100% { 
    opacity: 0.3; 
    transform: scale(0.8); 
    box-shadow: 0 0 4px currentColor; 
  }
  50% { 
    opacity: 0.9; 
    transform: scale(1); 
    box-shadow: 0 0 16px currentColor; 
  }
}

/* Waveform bars - for listening */
.mai-status-indicator__waveform {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 100%;
}

.mai-status-indicator__waveform-bar {
  width: 3px;
  border-radius: 1px;
  background: currentColor;
  transform-origin: bottom center;
  animation: mai-waveform 0.5s ease-in-out infinite;
}

.mai-status-indicator__waveform-bar:nth-child(1) { animation-delay: 0ms; }
.mai-status-indicator__waveform-bar:nth-child(2) { animation-delay: 50ms; }
.mai-status-indicator__waveform-bar:nth-child(3) { animation-delay: 100ms; }
.mai-status-indicator__waveform-bar:nth-child(4) { animation-delay: 150ms; }
.mai-status-indicator__waveform-bar:nth-child(5) { animation-delay: 200ms; }

@keyframes mai-waveform {
  0%, 100% { transform: scaleY(0.2); }
  50% { transform: scaleY(1); }
}

/* Thinking dots - for thinking */
.mai-status-indicator__dots {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  height: 100%;
}

.mai-status-indicator__dot-animated {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  animation: mai-thinking-dots 1.4s ease-in-out infinite;
}

.mai-status-indicator__dot-animated:nth-child(1) { animation-delay: 0ms; }
.mai-status-indicator__dot-animated:nth-child(2) { animation-delay: 200ms; }
.mai-status-indicator__dot-animated:nth-child(3) { animation-delay: 400ms; }

@keyframes mai-thinking-dots {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Speaking rings - for speaking */
.mai-status-indicator__rings {
  position: relative;
  width: 100%;
  height: 100%;
}

.mai-status-indicator__rings::before,
.mai-status-indicator__rings::after {
  content: '';
  position: absolute;
  inset: -4px;
  border: 2px solid currentColor;
  border-radius: 50%;
  opacity: 0;
  animation: mai-speaking-rings 1.5s ease-out infinite;
}

.mai-status-indicator__rings::after {
  animation-delay: 0.75s;
}

@keyframes mai-speaking-rings {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(3); opacity: 0; }
}

/* Spin - for processing */
@keyframes mai-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Dual spin - for updating */
.mai-status-indicator__dual-spin {
  position: relative;
  width: 100%;
  height: 100%;
}

.mai-status-indicator__dual-spin::before {
  content: '';
  position: absolute;
  inset: -2px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: mai-spin 1s linear infinite;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .mai-status-indicator__dot,
  .mai-status-indicator__waveform-bar,
  .mai-status-indicator__dot-animated,
  .mai-status-indicator__rings::before,
  .mai-status-indicator__rings::after,
  .mai-status-indicator__dual-spin::before {
    animation: none !important;
  }

  .mai-status-indicator__dot {
    transform: none !important;
    opacity: 1 !important;
    box-shadow: 0 0 8px currentColor !important;
  }

  .mai-status-indicator__waveform-bar {
    transform: scaleY(0.5) !important;
  }

  .mai-status-indicator__rings::before,
  .mai-status-indicator__rings::after {
    display: none !important;
  }
}

/* State-specific base styles */
.mai-status-indicator--idle .mai-status-indicator__dot {
  animation: mai-pulse 3s ease-in-out infinite;
}

.mai-status-indicator--listening .mai-status-indicator__dot {
  display: none;
}

.mai-status-indicator--listening .mai-status-indicator__waveform {
  display: inline-flex;
}

.mai-status-indicator--thinking .mai-status-indicator__dot {
  display: none;
}

.mai-status-indicator--thinking .mai-status-indicator__dots {
  display: inline-flex;
}

.mai-status-indicator--speaking .mai-status-indicator__dot {
  display: none;
}

.mai-status-indicator--speaking .mai-status-indicator__rings {
  display: block;
}

.mai-status-indicator--processing .mai-status-indicator__dot {
  animation: mai-spin 1s linear infinite;
}

.mai-status-indicator--sleeping .mai-status-indicator__dot {
  animation: mai-slow-pulse 6s ease-in-out infinite;
}

.mai-status-indicator--updating .mai-status-indicator__dot {
  display: none;
}

.mai-status-indicator--updating .mai-status-indicator__dual-spin {
  display: block;
}

.mai-status-indicator--offline .mai-status-indicator__dot {
  opacity: 0.5;
  box-shadow: none;
}

/* Tooltip */
.mai-status-indicator__tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-bg-elevated, #1D2028);
  border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 11px;
  color: var(--color-text-secondary, #A6B0BF);
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  z-index: 1000;
  transition: opacity 200ms ease-out, visibility 200ms;
}

.mai-status-indicator__tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--color-bg-elevated, #1D2028);
}

.mai-status-indicator:hover .mai-status-indicator__tooltip {
  opacity: 1;
  visibility: visible;
}

/* Focus visible */
.mai-status-indicator:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.4);
}
`;

// ============================================================================
// MAI STATUS INDICATOR CLASS
// ============================================================================

class MAIStatusIndicator {
  /**
   * Create a new MAI Status Indicator
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container selector or element
   * @param {string} options.size - Size: 'xs' | 'sm' | 'md' | 'lg' (default: 'md')
   * @param {boolean} options.showLabel - Show text label (default: false)
   * @param {string} options.initialState - Initial state (default: 'idle')
   * @param {Function} options.onStateChange - Callback when state changes
   * @param {boolean} options.tooltip - Show tooltip on hover (default: true)
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string' 
      ? document.querySelector(options.container) 
      : options.container;
    
    if (!this.container) {
      throw new Error('MAIStatusIndicator: Container not found');
    }

    this.size = options.size || 'md';
    this.showLabel = options.showLabel || false;
    this.tooltip = options.tooltip !== false;
    this.onStateChange = options.onStateChange || null;
    this.currentState = options.initialState || 'idle';
    this._stylesInjected = false;
    this._animationFrame = null;
    this._waveformBars = [];

    this._injectStyles();
    this._render();
    this.setState(this.currentState);
  }

  _injectStyles() {
    if (this._stylesInjected) return;
    
    const styleId = 'mai-status-indicator-styles';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = STYLES;
      document.head.appendChild(style);
    }
    this._stylesInjected = true;
  }

  _render() {
    const config = STATE_CONFIG[this.currentState];
    const sizeConfig = SIZE_CONFIG[this.size];

    this.container.innerHTML = '';
    this.container.className = 'mai-status-indicator';

    // Build class list
    const classes = [
      `mai-status-indicator--${this.size}`,
      `mai-status-indicator--${this.currentState}`
    ];

    if (this.showLabel) {
      classes.push('mai-status-indicator--with-label');
    }

    this.container.classList.add(...classes);
    this.container.style.setProperty('--dot-color', config.color);

    // Create dot element
    const dot = document.createElement('span');
    dot.className = 'mai-status-indicator__dot';
    dot.style.color = config.color;
    this.container.appendChild(dot);

    // Create animation-specific elements
    this._createAnimationElements(dot, config);

    // Create label if needed
    if (this.showLabel) {
      const label = document.createElement('span');
      label.className = 'mai-status-indicator__label';
      label.textContent = config.label;
      this.container.appendChild(label);
    }

    // Create tooltip
    if (this.tooltip) {
      const tooltip = document.createElement('span');
      tooltip.className = 'mai-status-indicator__tooltip';
      tooltip.textContent = config.ariaLabel;
      this.container.appendChild(tooltip);
    }

    // ARIA
    this.container.setAttribute('role', 'status');
    this.container.setAttribute('aria-live', 'polite');
    this.container.setAttribute('aria-label', config.ariaLabel);
    this.container.setAttribute('data-state', this.currentState);
  }

  _createAnimationElements(dot, config) {
    // Remove existing animation elements
    const existingAnimations = dot.querySelectorAll(
      '.mai-status-indicator__waveform, .mai-status-indicator__dots, .mai-status-indicator__rings, .mai-status-indicator__dual-spin'
    );
    existingAnimations.forEach(el => el.remove());

    switch (config.animation) {
      case 'waveform': {
        const waveform = document.createElement('span');
        waveform.className = 'mai-status-indicator__waveform';
        for (let i = 0; i < 5; i++) {
          const bar = document.createElement('span');
          bar.className = 'mai-status-indicator__waveform-bar';
          bar.style.color = config.color;
          bar.style.height = `${i % 2 === 0 ? '100%' : '60%'}`;
          waveform.appendChild(bar);
          this._waveformBars.push(bar);
        }
        dot.appendChild(waveform);
        break;
      }

      case 'dots': {
        const dots = document.createElement('span');
        dots.className = 'mai-status-indicator__dots';
        for (let i = 0; i < 3; i++) {
          const d = document.createElement('span');
          d.className = 'mai-status-indicator__dot-animated';
          d.style.color = config.color;
          dots.appendChild(d);
        }
        dot.appendChild(dots);
        break;
      }

      case 'rings': {
        const rings = document.createElement('span');
        rings.className = 'mai-status-indicator__rings';
        rings.style.color = config.color;
        dot.appendChild(rings);
        break;
      }

      case 'dual-spin': {
        const dualSpin = document.createElement('span');
        dualSpin.className = 'mai-status-indicator__dual-spin';
        dualSpin.style.color = config.color;
        dot.appendChild(dualSpin);
        break;
      }
    }
  }

  /**
   * Set the status state
   * @param {string} state - One of: idle, listening, thinking, speaking, processing, sleeping, updating, offline
   */
  setState(state) {
    if (!STATE_CONFIG[state]) {
      console.warn(`MAIStatusIndicator: Unknown state "${state}"`);
      return;
    }

    const prevState = this.currentState;
    this.currentState = state;

    // Re-render with new state
    this._render();

    // Trigger callback
    if (this.onStateChange && prevState !== state) {
      this.onStateChange(state, prevState);
    }

    // Emit custom event
    this.container.dispatchEvent(new CustomEvent('mai:statuschange', {
      detail: { state, prevState },
      bubbles: true
    }));
  }

  /**
   * Get current state
   * @returns {string}
   */
  getState() {
    return this.currentState;
  }

  /**
   * Set size
   * @param {string} size - 'xs' | 'sm' | 'md' | 'lg'
   */
  setSize(size) {
    if (!SIZE_CONFIG[size]) return;
    this.size = size;
    this._render();
    this.setState(this.currentState);
  }

  /**
   * Toggle label visibility
   * @param {boolean} show
   */
  setShowLabel(show) {
    this.showLabel = show;
    this._render();
    this.setState(this.currentState);
  }

  /**
   * Destroy the indicator
   */
  destroy() {
    if (this._animationFrame) {
      cancelAnimationFrame(this._animationFrame);
    }
    this.container.innerHTML = '';
    this.container.className = '';
  }
}

// ============================================================================
// FACTORY FUNCTIONS
// ============================================================================

/**
 * Create a status indicator for the topbar (compact)
 * @param {Object} options - Options
 * @returns {MAIStatusIndicator}
 */
function createTopbarIndicator(options = {}) {
  return new MAIStatusIndicator({
    ...options,
    size: 'sm',
    showLabel: false,
    tooltip: true
  });
}

/**
 * Create a status indicator for the bottombar (with label)
 * @param {Object} options - Options
 * @returns {MAIStatusIndicator}
 */
function createBottombarIndicator(options = {}) {
  return new MAIStatusIndicator({
    ...options,
    size: 'md',
    showLabel: true,
    tooltip: true
  });
}

/**
 * Create a status indicator for the presence page (large)
 * @param {Object} options - Options
 * @returns {MAIStatusIndicator}
 */
function createPresenceIndicator(options = {}) {
  return new MAIStatusIndicator({
    ...options,
    size: 'lg',
    showLabel: true,
    tooltip: false
  });
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  // Auto-initialize elements with data-mai-status attribute
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-status]').forEach(el => {
      const size = el.getAttribute('data-size') || 'md';
      const showLabel = el.hasAttribute('data-show-label');
      const initialState = el.getAttribute('data-state') || 'idle';
      
      new MAIStatusIndicator({
        container: el,
        size,
        showLabel,
        initialState
      });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MAIStatusIndicator,
    STATE_CONFIG,
    SIZE_CONFIG,
    createTopbarIndicator,
    createBottombarIndicator,
    createPresenceIndicator
  };
}

if (typeof window !== 'undefined') {
  window.MAIStatusIndicator = MAIStatusIndicator;
  window.createTopbarIndicator = createTopbarIndicator;
  window.createBottombarIndicator = createBottombarIndicator;
  window.createPresenceIndicator = createPresenceIndicator;
}

export { MAIStatusIndicator, STATE_CONFIG, SIZE_CONFIG, createTopbarIndicator, createBottombarIndicator, createPresenceIndicator };
export default MAIStatusIndicator;