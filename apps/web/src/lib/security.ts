/**
 * Frontend security utilities for input validation and sanitization
 */

/**
 * XSS patterns that should be blocked in any user input
 */
const XSS_PATTERNS = [
  '<script',
  '</script',
  'javascript:',
  'data:text/html',
  'data:application/javascript',
  'vbscript:',
  'onclick',
  'onerror',
  'onload',
  'onmouseover',
  'onfocus',
  'eval(',
  'alert(',
  'prompt(',
  'confirm(',
  'document.cookie',
  'window.location',
  'document.location',
  '.innerHTML',
  '.outerHTML',
  'document.write',
  'document.writeln',
  'document.domain',
  'document.body',
  '.parentNode',
  '.appendChild',
  'createElement',
  '.setAttribute'
];

/**
 * Suspicious hostnames that should be blocked
 */
const SUSPICIOUS_HOSTS = [
  'localhost',
  '127.0.0.1',
  '0.0.0.0',
  '::1',
  '169.254',  // Link-local addresses
  '10.',      // Private network
  '172.16.',  // Private network
  '192.168.'  // Private network
];

/**
 * Validate and sanitize a URL for safe usage
 */
export function sanitizeUrl(url: string): string | null {
  if (!url || typeof url !== 'string') return null;
  
  // Trim and normalize
  url = url.trim();
  
  // Special handling for blob URLs (safe, browser-generated)
  if (url.startsWith('blob:')) {
    return url;
  }
  
  try {
    const u = new URL(url);
    
    // Check protocol
    const allowedProtocols = process.env.NODE_ENV === 'development' 
      ? ['http:', 'https:'] 
      : ['https:'];
    
    if (!allowedProtocols.includes(u.protocol)) {
      console.warn(`[Security] Blocked URL with protocol: ${u.protocol}`);
      return null;
    }
    
    // Check for XSS patterns
    const urlLower = url.toLowerCase();
    for (const pattern of XSS_PATTERNS) {
      if (urlLower.includes(pattern.toLowerCase())) {
        console.warn(`[Security] Blocked URL containing XSS pattern: ${pattern}`);
        return null;
      }
    }
    
    // Check hostname
    for (const suspicious of SUSPICIOUS_HOSTS) {
      if (u.hostname.startsWith(suspicious)) {
        console.warn(`[Security] Blocked URL with suspicious hostname: ${u.hostname}`);
        return null;
      }
    }
    
    // URL is safe
    return url;
  } catch (e) {
    console.error('[Security] Invalid URL format:', e);
    return null;
  }
}

/**
 * Sanitize HTML content to prevent XSS
 * Note: For display, prefer using React's default escaping
 */
export function sanitizeHtml(html: string): string {
  if (!html || typeof html !== 'string') return '';
  
  // Basic HTML entity encoding
  return html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

/**
 * Validate user input for common injection attempts
 */
export function validateUserInput(
  input: string,
  maxLength: number = 10000,
  allowNewlines: boolean = true
): { valid: boolean; sanitized: string; error?: string } {
  if (!input || typeof input !== 'string') {
    return { valid: false, sanitized: '', error: 'Invalid input type' };
  }
  
  // Length check
  if (input.length > maxLength) {
    return { 
      valid: false, 
      sanitized: input.slice(0, maxLength), 
      error: `Input exceeds maximum length of ${maxLength} characters` 
    };
  }
  
  // Check for XSS patterns
  const inputLower = input.toLowerCase();
  for (const pattern of XSS_PATTERNS) {
    if (inputLower.includes(pattern.toLowerCase())) {
      return { 
        valid: false, 
        sanitized: sanitizeHtml(input), 
        error: `Input contains potentially dangerous content: ${pattern}` 
      };
    }
  }
  
  // Check for SQL injection patterns (basic)
  const sqlPatterns = [
    'drop table',
    'delete from',
    'insert into',
    'select * from',
    'union select',
    'or 1=1',
    'or true',
    '; --',
    '/*',
    '*/',
    'xp_cmdshell',
    'exec(',
    'execute(',
    'sp_executesql'
  ];
  
  for (const pattern of sqlPatterns) {
    if (inputLower.includes(pattern)) {
      return { 
        valid: false, 
        sanitized: sanitizeHtml(input), 
        error: 'Input contains potentially dangerous SQL pattern' 
      };
    }
  }
  
  // Sanitize but allow
  let sanitized = input;
  
  // Remove null bytes (replace with space to maintain word separation)
  sanitized = sanitized.replace(/\0/g, ' ');
  
  // Normalize whitespace if needed
  if (!allowNewlines) {
    sanitized = sanitized.replace(/[\r\n]+/g, ' ');
  }
  
  // Trim excessive whitespace
  sanitized = sanitized.replace(/\s+/g, ' ').trim();
  
  return { valid: true, sanitized };
}

/**
 * Create a Content Security Policy header value
 */
export function generateCSP(nonce?: string): string {
  const policies = [
    "default-src 'self'",
    `script-src 'self' ${nonce ? `'nonce-${nonce}'` : "'unsafe-inline'"} https://clerk.com https://*.clerk.accounts.dev`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    "connect-src 'self' https://api.openrouter.ai https://clerk.com https://*.clerk.accounts.dev wss://websocket.example.com",
    "frame-src 'self' https://clerk.com https://*.clerk.accounts.dev",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests"
  ];
  
  return policies.join('; ');
}

/**
 * Validate file upload
 */
export function validateFileUpload(
  file: File,
  allowedTypes: string[] = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  maxSizeBytes: number = 10 * 1024 * 1024 // 10MB
): { valid: boolean; error?: string } {
  // Check file size
  if (file.size > maxSizeBytes) {
    return { 
      valid: false, 
      error: `File size exceeds maximum of ${maxSizeBytes / 1024 / 1024}MB` 
    };
  }
  
  // Check MIME type
  if (!allowedTypes.includes(file.type)) {
    return { 
      valid: false, 
      error: `File type ${file.type} is not allowed. Allowed types: ${allowedTypes.join(', ')}` 
    };
  }
  
  // Check for suspicious file names first (before extension validation)
  const suspiciousPatterns = [
    '.exe',
    '.dll',
    '.bat',
    '.cmd',
    '.sh',
    '.ps1',
    '.vbs',
    '.js',
    '.jar',
    '.app',
    '.dmg',
    '.pkg'
  ];
  
  const nameLower = file.name.toLowerCase();
  for (const pattern of suspiciousPatterns) {
    if (nameLower.includes(pattern)) {
      return { 
        valid: false, 
        error: `File name contains suspicious pattern: ${pattern}` 
      };
    }
  }
  
  // Check file extension matches MIME type
  const extension = file.name.split('.').pop()?.toLowerCase();
  const expectedExtensions: Record<string, string[]> = {
    'image/jpeg': ['jpg', 'jpeg'],
    'image/png': ['png'],
    'image/gif': ['gif'],
    'image/webp': ['webp'],
    'application/pdf': ['pdf']
  };
  
  const validExtensions = expectedExtensions[file.type];
  if (validExtensions && extension && !validExtensions.includes(extension)) {
    return { 
      valid: false, 
      error: `File extension .${extension} doesn't match MIME type ${file.type}` 
    };
  }
  
  return { valid: true };
}

/**
 * Generate a cryptographically secure nonce for CSP
 */
export function generateNonce(): string {
  if (typeof window !== 'undefined' && window.crypto) {
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }
  // Fallback for SSR
  return Math.random().toString(36).substring(2, 15);
}