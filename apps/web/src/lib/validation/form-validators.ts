/**
 * Comprehensive form validation utilities
 */

export interface ValidationRule {
  validate: (value: any) => boolean;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export interface FieldValidator {
  name: string;
  rules: ValidationRule[];
}

// Common validation rules
export const validators = {
  required: (message = 'This field is required'): ValidationRule => ({
    validate: (value) => {
      if (value === null || value === undefined) return false;
      if (typeof value === 'string') return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    },
    message
  }),

  email: (message = 'Please enter a valid email address'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true; // Skip if empty (use with required)
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(value);
    },
    message
  }),

  minLength: (min: number, message?: string): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return value.length >= min;
    },
    message: message || `Must be at least ${min} characters`
  }),

  maxLength: (max: number, message?: string): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return value.length <= max;
    },
    message: message || `Must be no more than ${max} characters`
  }),

  pattern: (regex: RegExp, message = 'Invalid format'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return regex.test(value);
    },
    message
  }),

  url: (message = 'Please enter a valid URL'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message
  }),

  number: (message = 'Must be a number'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return !isNaN(Number(value));
    },
    message
  }),

  min: (min: number, message?: string): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return Number(value) >= min;
    },
    message: message || `Must be at least ${min}`
  }),

  max: (max: number, message?: string): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return Number(value) <= max;
    },
    message: message || `Must be no more than ${max}`
  }),

  hexColor: (message = 'Must be a valid hex color (e.g., #FF0000)'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(value);
    },
    message
  }),

  dimensions: (message = 'Must be in format WIDTHxHEIGHT (e.g., 1920x1080)'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return /^\d+x\d+$/.test(value);
    },
    message
  }),

  fileType: (allowedTypes: string[], message?: string): ValidationRule => ({
    validate: (file: File) => {
      if (!file) return true;
      const extension = file.name.split('.').pop()?.toLowerCase();
      return allowedTypes.includes(extension || '');
    },
    message: message || `File type must be one of: ${allowedTypes.join(', ')}`
  }),

  fileSize: (maxSizeInMB: number, message?: string): ValidationRule => ({
    validate: (file: File) => {
      if (!file) return true;
      return file.size <= maxSizeInMB * 1024 * 1024;
    },
    message: message || `File size must be less than ${maxSizeInMB}MB`
  }),

  custom: (
    validateFn: (value: any) => boolean | Promise<boolean>,
    message: string
  ): ValidationRule => ({
    validate: validateFn,
    message
  })
};

// Validate a single field
export function validateField(value: any, rules: ValidationRule[]): ValidationResult {
  const errors: string[] = [];
  
  for (const rule of rules) {
    if (!rule.validate(value)) {
      errors.push(rule.message);
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

// Validate multiple fields
export function validateForm(
  data: Record<string, any>,
  validators: FieldValidator[]
): Record<string, ValidationResult> {
  const results: Record<string, ValidationResult> = {};
  
  for (const validator of validators) {
    results[validator.name] = validateField(data[validator.name], validator.rules);
  }
  
  return results;
}

// Check if form is valid
export function isFormValid(results: Record<string, ValidationResult>): boolean {
  return Object.values(results).every(result => result.valid);
}

// Get all form errors
export function getFormErrors(results: Record<string, ValidationResult>): string[] {
  const errors: string[] = [];
  
  for (const [field, result] of Object.entries(results)) {
    if (!result.valid) {
      errors.push(...result.errors.map(error => `${field}: ${error}`));
    }
  }
  
  return errors;
}

// React hook for form validation
export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  validators: FieldValidator[]
) {
  const [values, setValues] = React.useState(initialValues);
  const [errors, setErrors] = React.useState<Record<string, string[]>>({});
  const [touched, setTouched] = React.useState<Record<string, boolean>>({});
  
  const validateField = React.useCallback((name: string, value: any) => {
    const validator = validators.find(v => v.name === name);
    if (!validator) return;
    
    const result = validateField(value, validator.rules);
    setErrors(prev => ({
      ...prev,
      [name]: result.errors
    }));
  }, [validators]);
  
  const handleChange = React.useCallback((name: string, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }));
    
    if (touched[name]) {
      validateField(name, value);
    }
  }, [touched, validateField]);
  
  const handleBlur = React.useCallback((name: string) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    validateField(name, values[name]);
  }, [values, validateField]);
  
  const validateAll = React.useCallback(() => {
    const results = validateForm(values, validators);
    const newErrors: Record<string, string[]> = {};
    
    for (const [field, result] of Object.entries(results)) {
      if (!result.valid) {
        newErrors[field] = result.errors;
      }
    }
    
    setErrors(newErrors);
    setTouched(Object.keys(values).reduce((acc, key) => ({ ...acc, [key]: true }), {}));
    
    return Object.keys(newErrors).length === 0;
  }, [values, validators]);
  
  const reset = React.useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);
  
  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateAll,
    reset,
    isValid: Object.keys(errors).length === 0
  };
}

// Input wrapper component
export function FormField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  onBlur,
  error,
  touched,
  required,
  placeholder,
  className = ''
}: {
  label: string;
  name: string;
  type?: string;
  value: any;
  onChange: (value: any) => void;
  onBlur: () => void;
  error?: string[];
  touched?: boolean;
  required?: boolean;
  placeholder?: string;
  className?: string;
}) {
  const hasError = touched && error && error.length > 0;
  
  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        className={`
          w-full px-3 py-2 border rounded-md shadow-sm
          focus:ring-blue-500 focus:border-blue-500
          ${hasError ? 'border-red-300' : 'border-gray-300'}
        `}
        aria-invalid={hasError}
        aria-describedby={hasError ? `${name}-error` : undefined}
      />
      {hasError && (
        <div id={`${name}-error`} className="text-sm text-red-600">
          {error.join(', ')}
        </div>
      )}
    </div>
  );
}

import React from 'react';