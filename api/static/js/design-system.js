/**
 * MAI Cognitive Operating System - Design System Utilities
 * JavaScript utilities for working with design tokens programmatically
 * 
 * Usage:
 * import { tokens, getToken, createTheme, mediaQuery } from './design-system.js';
 */

// ============================================================================
// DESIGN TOKENS (mirror of CSS custom properties)
// ============================================================================

export const tokens = {
  colors: {
    // Backgrounds
    bgPrimary: '#0A0B0F',
    bgSecondary: '#0E1015',
    bgPanel: '#12141A',
    bgCard: '#181B22',
    bgElevated: '#1D2028',

    // Borders
    borderSubtle: 'rgba(255, 255, 255, 0.07)',
    borderDefault: 'rgba(255, 255, 255, 0.10)',
    borderStrong: 'rgba(255, 255, 255, 0.15)',

    // Text
    textPrimary: '#F2F5FA',
    textSecondary: '#A6B0BF',
    textMuted: '#6E7785',

    // Accents
    accentPrimary: '#7C5CFF',
    accentSoft: '#9B86FF',
    accentBlue: '#6EA8FF',

    // Semantic
    success: '#72D6A5',
    warning: '#E8B86A',
    danger: '#E87575',

    // Status
    status: {
      idle: '#7C5CFF',
      listening: '#6EA8FF',
      thinking: '#9B86FF',
      speaking: '#72D6A5',
      processing: '#E8B86A',
      sleeping: '#7C5CFF',
      updating: '#6EA8FF',
      offline: '#6E7785'
    }
  },

  typography: {
    fontSans: ['Inter', 'Manrope', 'Space Grotesk', 'system-ui', '-apple-system', 'sans-serif'],
    fontMono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],

    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem'
    },

    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },

    lineHeight: {
      tight: 1.1,
      snug: 1.3,
      normal: 1.5,
      relaxed: 1.6
    },

    letterSpacing: {
      tight: '-0.02em',
      normal: '0',
      wide: '0.02em',
      wider: '0.08em'
    }
  },

  spacing: {
    0: '0',
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    8: '2rem',
    10: '2.5rem',
    12: '3rem',
    16: '4rem',
    20: '5rem',
    24: '6rem'
  },

  borderRadius: {
    sm: '8px',
    md: '10px',
    lg: '12px',
    xl: '16px',
    '2xl': '20px',
    full: '9999px'
  },

  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
    md: '0 4px 12px rgba(0, 0, 0, 0.4)',
    lg: '0 8px 32px rgba(0, 0, 0, 0.5)',
    glow: '0 0 20px rgba(124, 92, 255, 0.3)',
    glowSoft: '0 0 12px rgba(124, 92, 255, 0.15)'
  },

  transitions: {
    fast: '150ms ease-out',
    normal: '250ms ease-out',
    slow: '500ms ease-out',
    cinematic: '1000ms ease-out'
  },

  easing: {
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    easeOut: 'cubic-bezier(0.23, 1, 0.32, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)'
  },

  zIndex: {
    dropdown: 100,
    sticky: 200,
    sidebar: 300,
    header: 400,
    modal: 500,
    popover: 600,
    tooltip: 700,
    commandPalette: 900,
    toastContainer: 1000
  },

  layout: {
    sidebar: {
      collapsed: '72px',
      expanded: '220px'
    },
    topbar: '48px',
    bottombar: '64px',
    rightPanel: '320px'
  },

  breakpoints: {
    xs: '320px',
    sm: '375px',
    md: '768px',
    lg: '1024px',
    xl: '1440px',
    '2xl': '1920px'
  }
};

// ============================================================================
// TOKEN ACCESS UTILITIES
// ============================================================================

/**
 * Get a design token value by path
 * @param {string} path - Dot notation path (e.g., 'colors.accentPrimary')
 * @param {any} fallback - Fallback value if token not found
 * @returns {any} Token value or fallback
 */
export function getToken(path, fallback = undefined) {
  const keys = path.split('.');
  let value = tokens;
  
  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      return fallback;
    }
  }
  
  return value;
}

/**
 * Get CSS custom property value from computed styles
 * @param {string} propertyName - CSS variable name (e.g., '--color-accent-primary')
 * @param {Element} element - Element to read from (default: document.documentElement)
 * @returns {string} Computed value
 */
export function getCSSVar(propertyName, element = document.documentElement) {
  return getComputedStyle(element).getPropertyValue(propertyName).trim();
}

/**
 * Set CSS custom property on element
 * @param {string} propertyName - CSS variable name
 * @param {string} value - Value to set
 * @param {Element} element - Element to set on (default: document.documentElement)
 */
export function setCSSVar(propertyName, value, element = document.documentElement) {
  element.style.setProperty(propertyName, value);
}

/**
 * Get all CSS custom properties as object
 * @param {Element} element - Element to read from (default: document.documentElement)
 * @returns {Object} Map of CSS variables
 */
export function getAllCSSVars(element = document.documentElement) {
  const styles = getComputedStyle(element);
  const vars = {};
  
  for (let i = 0; i < styles.length; i++) {
    const prop = styles[i];
    if (prop.startsWith('--')) {
      vars[prop] = styles.getPropertyValue(prop).trim();
    }
  }
  
  return vars;
}

// ============================================================================
// COLOR UTILITIES
// ============================================================================

/**
 * Convert hex color to rgba
 * @param {string} hex - Hex color (e.g., '#7C5CFF')
 * @param {number} alpha - Alpha value (0-1)
 * @returns {string} RGBA string
 */
export function hexToRgba(hex, alpha = 1) {
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.slice(0, 2), 16);
  const g = parseInt(cleanHex.slice(2, 4), 16);
  const b = parseInt(cleanHex.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Generate color scale from base color
 * @param {string} baseColor - Base hex color
 * @param {number} steps - Number of steps (default: 10)
 * @returns {string[]} Array of hex colors
 */
export function generateColorScale(baseColor, steps = 10) {
  // Simple implementation - in production use a proper color library
  const scale = [baseColor];
  const base = hexToRgb(baseColor);
  
  for (let i = 1; i < steps; i++) {
    const factor = i / steps;
    const r = Math.round(base.r * (1 - factor));
    const g = Math.round(base.g * (1 - factor));
    const b = Math.round(base.b * (1 - factor));
    scale.push(`#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`);
  }
  
  return scale;
}

function hexToRgb(hex) {
  const cleanHex = hex.replace('#', '');
  return {
    r: parseInt(cleanHex.slice(0, 2), 16),
    g: parseInt(cleanHex.slice(2, 4), 16),
    b: parseInt(cleanHex.slice(4, 6), 16)
  };
}

/**
 * Check if color is light or dark
 * @param {string} hex - Hex color
 * @returns {boolean} True if light
 */
export function isLightColor(hex) {
  const { r, g, b } = hexToRgb(hex);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5;
}

/**
 * Get contrasting text color for background
 * @param {string} backgroundHex - Background color
 * @returns {string} 'white' or 'black'
 */
export function getContrastColor(backgroundHex) {
  return isLightColor(backgroundHex) ? '#000000' : '#FFFFFF';
}

// ============================================================================
// MEDIA QUERY UTILITIES
// ============================================================================

/**
 * Create media query matcher
 * @param {string} breakpoint - Breakpoint key from tokens.breakpoints
 * @returns {MediaQueryList} Media query list
 */
export function mediaQuery(breakpoint) {
  const bp = tokens.breakpoints[breakpoint];
  if (!bp) throw new Error(`Unknown breakpoint: ${breakpoint}`);
  return window.matchMedia(`(min-width: ${bp})`);
}

/**
 * Check if current viewport matches breakpoint
 * @param {string} breakpoint - Breakpoint key
 * @returns {boolean} True if matches
 */
export function matchesBreakpoint(breakpoint) {
  return mediaQuery(breakpoint).matches;
}

/**
 * Get current active breakpoint
 * @returns {string} Current breakpoint key
 */
export function getCurrentBreakpoint() {
  const breakpoints = ['2xl', 'xl', 'lg', 'md', 'sm', 'xs'];
  
  for (const bp of breakpoints) {
    if (matchesBreakpoint(bp)) return bp;
  }
  
  return 'xs';
}

/**
 * Add listener for breakpoint changes
 * @param {string} breakpoint - Breakpoint key
 * @param {Function} callback - Callback function (matches: boolean) => void
 * @returns {Function} Cleanup function
 */
export function onBreakpointChange(breakpoint, callback) {
  const mq = mediaQuery(breakpoint);
  const handler = (e) => callback(e.matches);
  
  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}

/**
 * Reduced motion preference
 * @returns {boolean} True if reduced motion preferred
 */
export function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Dark mode preference
 * @returns {boolean} True if dark mode preferred
 */
export function prefersDarkMode() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

// ============================================================================
// ANIMATION UTILITIES
// ============================================================================

/**
 * Create Anime.js animation config from design tokens
 * @param {Object} config - Animation config
 * @returns {Object} Anime.js compatible config
 */
export function createAnimeConfig(config) {
  const {
    duration = 'normal',
    easing = 'easeOut',
    delay = 0,
    ...rest
  } = config;

  return {
    duration: typeof duration === 'string' ? parseTransitionDuration(duration) : duration,
    easing: typeof easing === 'string' ? tokens.transitions[easing] || easing : easing,
    delay,
    ...rest
  };
}

function parseTransitionDuration(duration) {
  const map = {
    fast: 150,
    normal: 250,
    slow: 500,
    cinematic: 1000
  };
  return map[duration] || 250;
}

/**
 * Stagger delay calculator
 * @param {number} index - Item index
 * @param {number} baseDelay - Base delay in ms
 * @param {number} stagger - Stagger amount in ms
 * @returns {number} Calculated delay
 */
export function staggerDelay(index, baseDelay = 0, stagger = 80) {
  return baseDelay + (index * stagger);
}

/**
 * Create spring config for Framer Motion
 * @param {Object} options - Spring options
 * @returns {Object} Framer Motion spring config
 */
export function createSpringConfig(options = {}) {
  return {
    type: 'spring',
    damping: 25,
    stiffness: 180,
    mass: 1,
    ...options
  };
}

/**
 * Create tween config for Framer Motion
 * @param {Object} options - Tween options
 * @returns {Object} Framer Motion tween config
 */
export function createTweenConfig(options = {}) {
  return {
    type: 'tween',
    ease: [0.23, 1, 0.32, 1], // easing.easeOut
    duration: 0.25,
    ...options
  };
}

// ============================================================================
// LAYOUT UTILITIES
// ============================================================================

/**
 * Calculate responsive grid columns
 * @param {number} containerWidth - Container width in px
 * @param {number} minItemWidth - Minimum item width in px
 * @param {number} gap - Gap in px
 * @returns {number} Number of columns
 */
export function calculateGridColumns(containerWidth, minItemWidth, gap = 16) {
  return Math.max(1, Math.floor((containerWidth + gap) / (minItemWidth + gap)));
}

/**
 * Get sidebar width based on state
 * @param {boolean} expanded - Whether sidebar is expanded
 * @returns {string} Width value
 */
export function getSidebarWidth(expanded) {
  return expanded ? tokens.layout.sidebar.expanded : tokens.layout.sidebar.collapsed;
}

/**
 * Get right panel width based on state
 * @param {boolean} open - Whether panel is open
 * @returns {string} Width value
 */
export function getRightPanelWidth(open) {
  return open ? tokens.layout.rightPanel : '0';
}

// ============================================================================
// COMPONENT CLASS GENERATORS
// ============================================================================

/**
 * Generate BEM-style class names
 * @param {string} block - Block name
 * @param {Object} modifiers - Modifier states
 * @returns {string} Class string
 */
export function cn(block, modifiers = {}) {
  const classes = [block];
  
  for (const [modifier, value] of Object.entries(modifiers)) {
    if (value === true) {
      classes.push(`${block}--${modifier}`);
    } else if (typeof value === 'string') {
      classes.push(`${block}--${modifier}--${value}`);
    }
  }
  
  return classes.join(' ');
}

/**
 * Merge class names (like clsx)
 * @param {...(string|Object|Array)} args - Class names
 * @returns {string} Merged class string
 */
export function mergeClasses(...args) {
  const classes = [];
  
  for (const arg of args) {
    if (!arg) continue;
    
    if (typeof arg === 'string') {
      classes.push(arg);
    } else if (Array.isArray(arg)) {
      classes.push(mergeClasses(...arg));
    } else if (typeof arg === 'object') {
      for (const [key, value] of Object.entries(arg)) {
        if (value) classes.push(key);
      }
    }
  }
  
  return classes.join(' ');
}

// ============================================================================
// DEBOUNCE / THROTTLE
// ============================================================================

/**
 * Debounce function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in ms
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Throttle function
 * @param {Function} fn - Function to throttle
 * @param {number} limit - Limit in ms
 * @returns {Function} Throttled function
 */
export function throttle(fn, limit) {
  let inThrottle;
  return (...args) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// ============================================================================
// THEME MANAGEMENT
// ============================================================================

/**
 * Apply theme to document
 * @param {Object} theme - Theme object with color overrides
 */
export function applyTheme(theme) {
  const root = document.documentElement;
  
  for (const [key, value] of Object.entries(theme)) {
    const cssVar = `--color-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
    root.style.setProperty(cssVar, value);
  }
}

/**
 * Reset theme to defaults
 */
export function resetTheme() {
  const root = document.documentElement;
  const style = getComputedStyle(root);
  
  for (let i = 0; i < style.length; i++) {
    const prop = style[i];
    if (prop.startsWith('--color-') && root.style.getPropertyValue(prop)) {
      root.style.removeProperty(prop);
    }
  }
}

/**
 * Get current theme as object
 * @returns {Object} Current theme colors
 */
export function getCurrentTheme() {
  const root = document.documentElement;
  const theme = {};
  
  for (let i = 0; i < style.length; i++) {
    const prop = style[i];
    if (prop.startsWith('--color-')) {
      const key = prop.slice(8).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      theme[key] = style.getPropertyValue(prop).trim();
    }
  }
  
  return theme;
}

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  tokens,
  getToken,
  getCSSVar,
  setCSSVar,
  getAllCSSVars,
  hexToRgba,
  generateColorScale,
  isLightColor,
  getContrastColor,
  mediaQuery,
  matchesBreakpoint,
  getCurrentBreakpoint,
  onBreakpointChange,
  prefersReducedMotion,
  prefersDarkMode,
  createAnimeConfig,
  staggerDelay,
  createSpringConfig,
  createTweenConfig,
  calculateGridColumns,
  getSidebarWidth,
  getRightPanelWidth,
  cn,
  mergeClasses,
  debounce,
  throttle,
  applyTheme,
  resetTheme,
  getCurrentTheme
};