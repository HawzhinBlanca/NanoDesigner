/**
 * Frontend validation schemas for request size and input validation
 */

// Constants for validation limits
export const VALIDATION_LIMITS = {
  PROMPT: {
    MIN_LENGTH: 5,
    MAX_LENGTH: 2000,
  },
  REFERENCE_URL: {
    MAX_LENGTH: 2048,
    MAX_COUNT: 10,
  },
  REQUEST: {
    MAX_BODY_SIZE: 1 * 1024 * 1024, // 1MB for JSON payloads
  }
};

/**
 * Sanitize and validate user input
 */
export function sanitizeInput(input: string, maxLength: number = VALIDATION_LIMITS.PROMPT.MAX_LENGTH): string {
  if (!input || typeof input !== 'string') return '';
  
  // Start with original input (don't trim during typing)
  let sanitized = input;
  
  // Remove null bytes
  sanitized = sanitized.replace(/\0/g, '');
  
  // Enforce max length
  if (sanitized.length > maxLength) {
    sanitized = sanitized.slice(0, maxLength);
  }
  
  // Remove any HTML tags for safety
  sanitized = sanitized.replace(/<[^>]*>/g, '');
  
  return sanitized;
}
