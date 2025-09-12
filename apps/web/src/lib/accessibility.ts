// Accessibility utilities and hooks

import { useEffect, useCallback } from 'react';

// Keyboard navigation hook
export function useKeyboardNavigation() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip to main content
      if (e.key === 'Tab' && e.shiftKey && e.altKey) {
        e.preventDefault();
        const main = document.querySelector('main');
        if (main) {
          (main as HTMLElement).focus();
          (main as HTMLElement).scrollIntoView({ behavior: 'smooth' });
        }
      }

      // Escape key to close modals
      if (e.key === 'Escape') {
        const event = new CustomEvent('closeModal');
        window.dispatchEvent(event);
      }

      // Arrow key navigation for grids
      if (e.key.startsWith('Arrow') && e.target instanceof HTMLElement) {
        const grid = e.target.closest('[role="grid"]');
        if (grid) {
          handleGridNavigation(e, grid as HTMLElement);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
}

// Grid navigation handler
function handleGridNavigation(e: KeyboardEvent, grid: HTMLElement) {
  e.preventDefault();
  const cells = Array.from(grid.querySelectorAll('[role="gridcell"]'));
  const currentIndex = cells.findIndex(cell => cell === document.activeElement);
  
  if (currentIndex === -1) return;

  const columns = parseInt(grid.getAttribute('aria-colcount') || '1');
  let newIndex = currentIndex;

  switch (e.key) {
    case 'ArrowRight':
      newIndex = Math.min(currentIndex + 1, cells.length - 1);
      break;
    case 'ArrowLeft':
      newIndex = Math.max(currentIndex - 1, 0);
      break;
    case 'ArrowDown':
      newIndex = Math.min(currentIndex + columns, cells.length - 1);
      break;
    case 'ArrowUp':
      newIndex = Math.max(currentIndex - columns, 0);
      break;
  }

  (cells[newIndex] as HTMLElement).focus();
}

// Focus trap hook for modals
export function useFocusTrap(ref: React.RefObject<HTMLElement>, isActive: boolean) {
  useEffect(() => {
    if (!isActive || !ref.current) return;

    const element = ref.current;
    const focusableElements = element.querySelectorAll(
      'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select, [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0] as HTMLElement;
    const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    };

    element.addEventListener('keydown', handleTabKey);
    firstFocusable?.focus();

    return () => {
      element.removeEventListener('keydown', handleTabKey);
    };
  }, [ref, isActive]);
}

// Announce changes to screen readers
export function useAnnounce() {
  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcer = document.createElement('div');
    announcer.setAttribute('role', 'status');
    announcer.setAttribute('aria-live', priority);
    announcer.setAttribute('aria-atomic', 'true');
    announcer.style.position = 'absolute';
    announcer.style.left = '-10000px';
    announcer.style.width = '1px';
    announcer.style.height = '1px';
    announcer.style.overflow = 'hidden';
    
    announcer.textContent = message;
    document.body.appendChild(announcer);

    setTimeout(() => {
      document.body.removeChild(announcer);
    }, 1000);
  }, []);

  return announce;
}

// Check if user prefers reduced motion
export function usePrefersReducedMotion(): boolean {
  const query = '(prefers-reduced-motion: reduce)';
  
  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = () => {
      document.documentElement.classList.toggle('reduce-motion', mediaQuery.matches);
    };

    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return window.matchMedia(query).matches;
}

// High contrast mode detection
export function usePrefersHighContrast(): boolean {
  const query = '(prefers-contrast: high)';
  
  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = () => {
      document.documentElement.classList.toggle('high-contrast', mediaQuery.matches);
    };

    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return window.matchMedia(query).matches;
}

// ARIA labels for common patterns
export const ariaLabels = {
  navigation: {
    main: 'Main navigation',
    breadcrumb: 'Breadcrumb navigation',
    pagination: 'Pagination navigation',
    social: 'Social media links',
  },
  buttons: {
    close: 'Close',
    menu: 'Open menu',
    search: 'Search',
    submit: 'Submit form',
    cancel: 'Cancel',
    delete: 'Delete item',
    edit: 'Edit item',
    save: 'Save changes',
    generate: 'Generate design',
  },
  status: {
    loading: 'Loading, please wait',
    success: 'Operation completed successfully',
    error: 'An error occurred',
    warning: 'Warning',
    info: 'Information',
  },
  form: {
    required: 'Required field',
    optional: 'Optional field',
    error: 'Field has an error',
    helpText: 'Additional information',
  },
};

// Skip links component
export function SkipLinks() {
  return (
    <div className="sr-only focus-within:not-sr-only">
      <a 
        href="#main-content"
        className="absolute top-0 left-0 p-2 bg-primary text-primary-foreground z-50 focus:not-sr-only"
      >
        Skip to main content
      </a>
      <a 
        href="#main-navigation"
        className="absolute top-0 left-0 p-2 bg-primary text-primary-foreground z-50 focus:not-sr-only"
      >
        Skip to navigation
      </a>
    </div>
  );
}

// Focus visible styles
export const focusStyles = {
  ring: 'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
  outline: 'focus:outline-2 focus:outline-offset-2 focus:outline-primary',
  within: 'focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2',
};

// Accessible color contrast utilities
export const contrastColors = {
  highContrast: {
    text: 'text-black dark:text-white',
    background: 'bg-white dark:bg-black',
    border: 'border-black dark:border-white',
  },
  normal: {
    text: 'text-foreground',
    background: 'bg-background',
    border: 'border-border',
  },
};

// Screen reader only class
export const srOnly = 'sr-only focus:not-sr-only';

// Accessible loading states
export function LoadingAnnouncement({ message = 'Loading content' }: { message?: string }) {
  const announce = useAnnounce();
  
  useEffect(() => {
    announce(message, 'polite');
  }, [message, announce]);
  
  return null;
}

// Accessible error announcement
export function ErrorAnnouncement({ error }: { error: string }) {
  const announce = useAnnounce();
  
  useEffect(() => {
    if (error) {
      announce(`Error: ${error}`, 'assertive');
    }
  }, [error, announce]);
  
  return null;
}