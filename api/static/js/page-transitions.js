/**
 * MAI Page Transitions - Motion-style Page Transitions
 * Handles smooth page enter/exit animations with shared layout support
 * 
 * Usage:
 * import { MAIPageTransitions } from './page-transitions.js';
 * const transitions = new MAIPageTransitions({ container: '#main' });
 * await transitions.enter('chat');
 * await transitions.exit('presence');
 */

// ============================================================================
// TRANSITION PRESETS
// ============================================================================

const TRANSITION_PRESETS = {
  default: {
    enter: {
      opacity: [0, 1],
      translateY: [20, 0],
      scale: [0.98, 1]
    },
    exit: {
      opacity: [1, 0],
      translateY: [0, -20],
      scale: [1, 0.98]
    },
    duration: 0.5,
    ease: [0.23, 1, 0.32, 1] // cubic-bezier(0.23, 1, 0.32, 1)
  },
  
  slide: {
    enter: {
      opacity: [0, 1],
      translateX: [-30, 0]
    },
    exit: {
      opacity: [1, 0],
      translateX: [0, 30]
    },
    duration: 0.4,
    ease: [0.4, 0, 0.2, 1]
  },
  
  fade: {
    enter: { opacity: [0, 1] },
    exit: { opacity: [1, 0] },
    duration: 0.25,
    ease: 'ease-out'
  },
  
  zoom: {
    enter: {
      opacity: [0, 1],
      scale: [0.9, 1]
    },
    exit: {
      opacity: [1, 0],
      scale: [1, 0.9]
    },
    duration: 0.3,
    ease: [0.34, 1.56, 0.64, 1] // spring-like
  },
  
  none: {
    enter: {},
    exit: {},
    duration: 0,
    ease: 'linear'
  }
};

// ============================================================================
// MAI PAGE TRANSITIONS CLASS
// ============================================================================

class MAIPageTransitions {
  /**
   * Create a new MAI Page Transitions manager
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container for pages
   * @param {string} options.preset - Transition preset: 'default', 'slide', 'fade', 'zoom', 'none'
   * @param {Object} options.customTransition - Custom transition config
   * @param {boolean} options.useWAAPI - Use Web Animations API (default: true)
   * @param {Function} options.onEnterStart - Enter animation start callback
   * @param {Function} options.onEnterComplete - Enter animation complete callback
   * @param {Function} options.onExitStart - Exit animation start callback
   * @param {Function} options.onExitComplete - Exit animation complete callback
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAIPageTransitions: Container not found');
    }

    this.preset = options.preset || 'default';
    this.customTransition = options.customTransition || null;
    this.useWAAPI = options.useWAAPI !== false && 'animate' in Element.prototype;
    this.onEnterStart = options.onEnterStart || null;
    this.onEnterComplete = options.onEnterComplete || null;
    this.onExitStart = options.onExitStart || null;
    this.onExitComplete = options.onExitComplete || null;

    this._currentAnimation = null;
    this._reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this._boundMediaChange = this._handleMediaChange.bind(this);

    this._injectStyles();
    this._listenMediaChanges();
  }

  _injectStyles() {
    if (!document.getElementById('mai-page-transitions-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-page-transitions-styles';
      style.textContent = `
        .mai-page-transitioning {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
        }
        
        .mai-page-entering,
        .mai-page-exiting {
          will-change: transform, opacity;
        }
        
        /* Fallback CSS animations for when WAAPI not available */
        @keyframes mai-page-fade-enter {
          from { opacity: 0; transform: translateY(20px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        
        @keyframes mai-page-fade-exit {
          from { opacity: 1; transform: translateY(0) scale(1); }
          to { opacity: 0; transform: translateY(-20px) scale(0.98); }
        }
        
        @keyframes mai-page-slide-enter {
          from { opacity: 0; transform: translateX(-30px); }
          to { opacity: 1; transform: translateX(0); }
        }
        
        @keyframes mai-page-slide-exit {
          from { opacity: 1; transform: translateX(0); }
          to { opacity: 0; transform: translateX(30px); }
        }
        
        @keyframes mai-page-zoom-enter {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        
        @keyframes mai-page-zoom-exit {
          from { opacity: 1; transform: scale(1); }
          to { opacity: 0; transform: scale(0.9); }
        }
        
        .mai-page-enter-fallback {
          animation: mai-page-fade-enter 500ms cubic-bezier(0.23, 1, 0.32, 1) forwards;
        }
        
        .mai-page-exit-fallback {
          animation: mai-page-fade-exit 250ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        
        .mai-page-enter-slide-fallback {
          animation: mai-page-slide-enter 400ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        
        .mai-page-exit-slide-fallback {
          animation: mai-page-slide-exit 400ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        
        .mai-page-enter-zoom-fallback {
          animation: mai-page-zoom-enter 300ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }
        
        .mai-page-exit-zoom-fallback {
          animation: mai-page-zoom-exit 300ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        
        @media (prefers-reduced-motion: reduce) {
          .mai-page-enter-fallback,
          .mai-page-exit-fallback,
          .mai-page-enter-slide-fallback,
          .mai-page-exit-slide-fallback,
          .mai-page-enter-zoom-fallback,
          .mai-page-exit-zoom-fallback {
            animation: none !important;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  _listenMediaChanges() {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    mq.addEventListener('change', this._boundMediaChange);
  }

  _handleMediaChange(e) {
    this._reducedMotion = e.matches;
  }

  _getTransitionConfig() {
    if (this.customTransition) return this.customTransition;
    return TRANSITION_PRESETS[this.preset] || TRANSITION_PRESETS.default;
  }

  _getFallbackClass(phase) {
    const preset = this.preset;
    if (preset === 'slide') return `${phase}-slide-fallback`;
    if (preset === 'zoom') return `${phase}-zoom-fallback`;
    if (preset === 'fade') return `${phase}-fade-fallback`;
    return `${phase}-fallback`; // default
  }

  /**
   * Animate page enter
   * @param {string} pageId - Page identifier
   * @param {HTMLElement} element - Page element (optional, uses container's first child)
   * @returns {Promise<void>}
   */
  async enter(pageId, element = null) {
    if (this._reducedMotion) return Promise.resolve();

    const target = element || this.container.firstElementChild;
    if (!target) return Promise.resolve();

    const config = this._getTransitionConfig();
    const enterConfig = config.enter;
    const duration = (config.duration || 0.5) * 1000;

    if (this.onEnterStart) this.onEnterStart(pageId, target);

    return new Promise((resolve) => {
      if (this.useWAAPI && Object.keys(enterConfig).length > 0) {
        this._animateWAAPI(target, enterConfig, config, 'enter', resolve);
      } else {
        this._animateFallback(target, 'enter', duration, resolve);
      }
    });
  }

  /**
   * Animate page exit
   * @param {string} pageId - Page identifier
   * @param {HTMLElement} element - Page element (optional)
   * @returns {Promise<void>}
   */
  async exit(pageId, element = null) {
    if (this._reducedMotion) return Promise.resolve();

    const target = element || this.container.firstElementChild;
    if (!target) return Promise.resolve();

    const config = this._getTransitionConfig();
    const exitConfig = config.exit;
    const duration = (config.duration || 0.5) * 1000;

    if (this.onExitStart) this.onExitStart(pageId, target);

    return new Promise((resolve) => {
      if (this.useWAAPI && Object.keys(exitConfig).length > 0) {
        this._animateWAAPI(target, exitConfig, config, 'exit', resolve);
      } else {
        this._animateFallback(target, 'exit', duration, resolve);
      }
    });
  }

  _animateWAAPI(element, keyframes, config, phase, resolve) {
    // Cancel any existing animation
    if (this._currentAnimation) {
      this._currentAnimation.cancel();
    }

    // Prepare keyframes for WAAPI
    const waapiKeyframes = [];
    const props = Object.keys(keyframes);
    
    // Create keyframe objects
    const numFrames = props.length > 0 ? 2 : 1;
    for (let i = 0; i < numFrames; i++) {
      const frame = { offset: i / (numFrames - 1) || 0 };
      props.forEach(prop => {
        const values = keyframes[prop];
        if (Array.isArray(values) && values.length >= 2) {
          frame[prop] = values[i];
        }
      });
      waapiKeyframes.push(frame);
    }

    // If only one frame (static), add a second frame
    if (waapiKeyframes.length === 1) {
      const finalFrame = { ...waapiKeyframes[0], offset: 1 };
      props.forEach(prop => {
        const values = keyframes[prop];
        if (Array.isArray(values) && values.length >= 2) {
          finalFrame[prop] = values[1];
        }
      });
      waapiKeyframes.push(finalFrame);
    }

    const options = {
      duration: (config.duration || 0.5) * 1000,
      easing: config.ease || 'ease-out',
      fill: 'both'
    };

    try {
      this._currentAnimation = element.animate(waapiKeyframes, options);
      
      this._currentAnimation.onfinish = () => {
        this._currentAnimation = null;
        if (phase === 'enter') {
          element.classList.remove('mai-page-entering');
        } else {
          element.classList.remove('mai-page-exiting');
        }
        if (this.onEnterComplete && phase === 'enter') this.onEnterComplete(element);
        if (this.onExitComplete && phase === 'exit') this.onExitComplete(element);
        resolve();
      };
      
      this._currentAnimation.oncancel = () => {
        this._currentAnimation = null;
        resolve();
      };

      element.classList.add(phase === 'enter' ? 'mai-page-entering' : 'mai-page-exiting');
    } catch (e) {
      // Fallback to CSS animation
      this._animateFallback(element, phase, config.duration * 1000, resolve);
    }
  }

  _animateFallback(element, phase, duration, resolve) {
    const className = this._getFallbackClass(phase === 'enter' ? 'mai-page-enter' : 'mai-page-exit');
    element.classList.add(className);

    const handleAnimationEnd = () => {
      element.classList.remove(className);
      element.removeEventListener('animationend', handleAnimationEnd);
      element.removeEventListener('animationcancel', handleAnimationEnd);
      
      if (phase === 'enter' && this.onEnterComplete) this.onEnterComplete(element);
      if (phase === 'exit' && this.onExitComplete) this.onExitComplete(element);
      resolve();
    };

    element.addEventListener('animationend', handleAnimationEnd, { once: true });
    element.addEventListener('animationcancel', handleAnimationEnd, { once: true });

    // Safety timeout
    setTimeout(() => {
      if (element.classList.contains(className)) {
        element.classList.remove(className);
        resolve();
      }
    }, duration + 100);
  }

  /**
   * Crossfade between two pages
   * @param {string} fromPageId - Page leaving
   * @param {string} toPageId - Page entering
   * @param {HTMLElement} fromElement - Leaving element
   * @param {HTMLElement} toElement - Entering element
   * @returns {Promise<void>}
   */
  async crossfade(fromPageId, toPageId, fromElement, toElement) {
    if (this._reducedMotion) return Promise.resolve();

    const config = this._getTransitionConfig();
    const duration = (config.duration || 0.5) * 1000;

    // Position both elements absolutely
    fromElement.style.position = 'absolute';
    fromElement.style.top = '0';
    fromElement.style.left = '0';
    fromElement.style.right = '0';
    fromElement.style.bottom = '0';
    fromElement.style.zIndex = '1';

    toElement.style.position = 'absolute';
    toElement.style.top = '0';
    toElement.style.left = '0';
    toElement.style.right = '0';
    toElement.style.bottom = '0';
    toElement.style.zIndex = '2';
    toElement.style.opacity = '0';

    this.container.appendChild(toElement);

    return new Promise((resolve) => {
      // Fade out old, fade in new
      const exitAnim = fromElement.animate([
        { opacity: 1 },
        { opacity: 0 }
      ], {
        duration,
        easing: config.ease || 'ease-out',
        fill: 'forwards'
      });

      const enterAnim = toElement.animate([
        { opacity: 0 },
        { opacity: 1 }
      ], {
        duration,
        easing: config.ease || 'ease-out',
        fill: 'forwards'
      });

      Promise.all([
        exitAnim.finished,
        enterAnim.finished
      ]).then(() => {
        fromElement.remove();
        toElement.style.position = '';
        toElement.style.top = '';
        toElement.style.left = '';
        toElement.style.right = '';
        toElement.style.bottom = '';
        toElement.style.zIndex = '';
        toElement.style.opacity = '';
        resolve();
      }).catch(resolve);
    });
  }

  /**
   * Shared layout animation (for elements that persist across pages)
   * @param {HTMLElement} element - Element to animate
   * @param {Object} from - Starting layout { x, y, width, height }
   * @param {Object} to - Ending layout { x, y, width, height }
   * @param {Object} options - Animation options
   * @returns {Promise<void>}
   */
  async sharedLayout(element, from, to, options = {}) {
    if (this._reducedMotion) {
      Object.assign(element.style, to);
      return Promise.resolve();
    }

    const duration = options.duration || 300;
    const easing = options.easing || [0.23, 1, 0.32, 1];

    return new Promise((resolve) => {
      const anim = element.animate([
        { transform: `translate(${from.x}px, ${from.y}px)`, width: `${from.width}px`, height: `${from.height}px` },
        { transform: `translate(${to.x}px, ${to.y}px)`, width: `${to.width}px`, height: `${to.height}px` }
      ], {
        duration,
        easing,
        fill: 'both'
      });

      anim.onfinish = () => {
        Object.assign(element.style, {
          transform: `translate(${to.x}px, ${to.y}px)`,
          width: `${to.width}px`,
          height: `${to.height}px`
        });
        resolve();
      };
    });
  }

  /**
   * Set transition preset
   * @param {string} preset 
   */
  setPreset(preset) {
    if (TRANSITION_PRESETS[preset] || preset === 'custom') {
      this.preset = preset;
    }
  }

  /**
   * Enable/disable transitions
   * @param {boolean} enabled 
   */
  setEnabled(enabled) {
    this.useWAAPI = enabled && 'animate' in Element.prototype;
  }

  /**
   * Check if transitions are enabled
   * @returns {boolean}
   */
  isEnabled() {
    return this.useWAAPI && !this._reducedMotion;
  }

  /**
   * Destroy the transitions manager
   */
  destroy() {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    mq.removeEventListener('change', this._boundMediaChange);
    
    if (this._currentAnimation) {
      this._currentAnimation.cancel();
    }
  }
}

// ============================================================================
// MOTION-STYLE VARIANT EXPORTS (for React integration reference)
/*
// Framer Motion variants for React components
export const pageVariants = {
  initial: { opacity: 0, y: 20, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -20, scale: 0.98 },
  transition: { duration: 0.5, ease: [0.23, 1, 0.32, 1] }
};

export const layoutVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
  transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] }
};

export const staggerContainer = {
  animate: { transition: { staggerChildren: 0.08 } }
};

export const staggerItem = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }
};

export const modalVariants = {
  initial: { opacity: 0, scale: 0.95, y: 20 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.95, y: 20 },
  transition: { duration: 0.3, ease: [0.34, 1.56, 0.64, 1] }
};

export const sidebarVariants = {
  collapsed: { width: 72, transition: { duration: 0.3, ease: [0.23, 1, 0.32, 1] } },
  expanded: { width: 220, transition: { duration: 0.3, ease: [0.23, 1, 0.32, 1] } }
};

export const rightPanelVariants = {
  closed: { width: 0, opacity: 0, transition: { duration: 0.3 } },
  open: { width: 320, opacity: 1, transition: { duration: 0.3, ease: [0.23, 1, 0.32, 1] } }
};

export const toastVariants = {
  initial: { opacity: 0, x: '100%' },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: '100%' },
  transition: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }
};

export const dropdownVariants = {
  initial: { opacity: 0, y: -8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.2 }
};
*/

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-page-transitions]').forEach(el => {
      const preset = el.getAttribute('data-preset') || 'default';
      new MAIPageTransitions({ container: el, preset });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAIPageTransitions, TRANSITION_PRESETS };
}

if (typeof window !== 'undefined') {
  window.MAIPageTransitions = MAIPageTransitions;
}

export { MAIPageTransitions, TRANSITION_PRESETS };
export default MAIPageTransitions;