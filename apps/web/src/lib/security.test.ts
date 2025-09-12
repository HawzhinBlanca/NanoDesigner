import { describe, it, expect } from 'vitest';
import {
  sanitizeUrl,
  sanitizeHtml,
  validateUserInput,
  validateFileUpload
} from './security';

describe('Security Utils', () => {
  describe('sanitizeUrl', () => {
    it('should allow valid HTTPS URLs', () => {
      const url = 'https://example.com/image.jpg';
      expect(sanitizeUrl(url)).toBe(url);
    });

    it('should allow blob URLs', () => {
      const url = 'blob:http://localhost:3000/abc-123';
      expect(sanitizeUrl(url)).toBe(url);
    });

    it('should block javascript: protocol', () => {
      expect(sanitizeUrl('javascript:alert(1)')).toBeNull();
      expect(sanitizeUrl('JavaScript:alert(1)')).toBeNull();
    });

    it('should block data: URLs with HTML', () => {
      expect(sanitizeUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
      expect(sanitizeUrl('data:application/javascript,alert(1)')).toBeNull();
    });

    it('should block URLs with XSS patterns', () => {
      expect(sanitizeUrl('https://example.com?q=<script>alert(1)</script>')).toBeNull();
      expect(sanitizeUrl('https://example.com#onclick=alert(1)')).toBeNull();
      expect(sanitizeUrl('https://example.com/eval(1)')).toBeNull();
    });

    it('should block localhost and private IPs', () => {
      expect(sanitizeUrl('http://localhost/admin')).toBeNull();
      expect(sanitizeUrl('http://127.0.0.1/admin')).toBeNull();
      expect(sanitizeUrl('http://192.168.1.1/router')).toBeNull();
      expect(sanitizeUrl('http://10.0.0.1/internal')).toBeNull();
    });

    it('should handle invalid URLs gracefully', () => {
      expect(sanitizeUrl('not-a-url')).toBeNull();
      expect(sanitizeUrl('')).toBeNull();
      expect(sanitizeUrl(null as any)).toBeNull();
    });
  });

  describe('sanitizeHtml', () => {
    it('should escape HTML entities', () => {
      expect(sanitizeHtml('<script>alert(1)</script>'))
        .toBe('&lt;script&gt;alert(1)&lt;&#x2F;script&gt;');
      
      expect(sanitizeHtml('"hello" & \'world\''))
        .toBe('&quot;hello&quot; &amp; &#x27;world&#x27;');
    });

    it('should handle empty input', () => {
      expect(sanitizeHtml('')).toBe('');
      expect(sanitizeHtml(null as any)).toBe('');
    });
  });

  describe('validateUserInput', () => {
    it('should accept valid input', () => {
      const result = validateUserInput('Hello, this is a valid message!');
      expect(result.valid).toBe(true);
      expect(result.sanitized).toBe('Hello, this is a valid message!');
    });

    it('should reject input with XSS patterns', () => {
      const result = validateUserInput('Hello <script>alert(1)</script>');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('dangerous content');
    });

    it('should reject SQL injection attempts', () => {
      const result = validateUserInput("'; DROP TABLE users; --");
      expect(result.valid).toBe(false);
      expect(result.error).toContain('SQL pattern');
    });

    it('should enforce length limits', () => {
      const longInput = 'a'.repeat(101);
      const result = validateUserInput(longInput, 100);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('exceeds maximum length');
      expect(result.sanitized.length).toBe(100);
    });

    it('should remove null bytes', () => {
      const result = validateUserInput('Hello\0World');
      expect(result.valid).toBe(true);
      expect(result.sanitized).toBe('Hello World');
    });

    it('should normalize whitespace', () => {
      const result = validateUserInput('Hello    World', 1000, false);
      expect(result.valid).toBe(true);
      expect(result.sanitized).toBe('Hello World');
    });
  });

  describe('validateFileUpload', () => {
    it('should accept valid image files', () => {
      const file = new File(['content'], 'image.jpg', { type: 'image/jpeg' });
      const result = validateFileUpload(file);
      expect(result.valid).toBe(true);
    });

    it('should reject files that are too large', () => {
      const largeContent = new Uint8Array(11 * 1024 * 1024); // 11MB
      const file = new File([largeContent], 'large.jpg', { type: 'image/jpeg' });
      const result = validateFileUpload(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('exceeds maximum');
    });

    it('should reject invalid MIME types', () => {
      const file = new File(['content'], 'script.js', { type: 'application/javascript' });
      const result = validateFileUpload(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('not allowed');
    });

    it('should detect MIME type mismatches', () => {
      // Use a non-suspicious extension that still doesn't match the MIME type
      const file = new File(['content'], 'image.txt', { type: 'image/jpeg' });
      const result = validateFileUpload(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain("doesn't match MIME type");
    });

    it('should reject suspicious file names', () => {
      const file = new File(['content'], 'photo.jpg.exe', { type: 'image/jpeg' });
      const result = validateFileUpload(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('suspicious pattern');
    });
  });
});