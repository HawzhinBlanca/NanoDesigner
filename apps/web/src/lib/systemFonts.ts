/**
 * System font detection and management
 * Detects available system fonts and provides a curated list for design use
 */

// System fonts available on most macOS/Windows/Linux systems
const COMMON_SYSTEM_FONTS = [
  // Prioritized fonts for different languages
  "Verdana", // Primary English font
  "Noto Sans Arabic", // Primary Arabic/Kurdish font
  
  // macOS System Fonts
  "SF Pro Text",
  "SF Pro Display", 
  "SF Compact",
  "SF Compact Display",
  "SF Pro Rounded",
  "Helvetica Neue",
  "Helvetica",

  // Cross-platform fonts
  "Arial",
  "Arial Black", 
  "Georgia",
  "Times New Roman",
  "Times",
  "Tahoma",

  // Arabic/Kurdish fonts
  "Arabic Typesetting",
  "Traditional Arabic",
  "Simplified Arabic",
  "Baghdad",
  "Al Bayan",

  // Web fonts commonly installed
  "Inter",
  "Roboto", 
  "Inter 18pt",
  "Inter 24pt",
  "Inter 28pt",
  "Roboto Condensed",

  // Other common fonts
  "Arial Narrow",
  "Arial Rounded MT Bold",
  "Arial Unicode MS",
  "Bahij Helvetica Neue",
];

// Web-safe fallback fonts
const WEB_SAFE_FONTS = [
  "Inter",
  "Roboto", 
  "Open Sans",
  "Lato",
  "Montserrat",
  "Source Sans Pro",
  "Raleway",
  "Nunito",
  "Poppins",
  "Merriweather",
  "Playfair Display",
  "Georgia",
  "Times New Roman", 
  "Arial",
  "Helvetica",
  "Verdana",
  "Tahoma",
  "Trebuchet MS",
  "Impact",
  "Courier New",
  "Monaco",
  "Menlo"
];

/**
 * Check if a font is available on the system
 * Uses canvas text measurement to detect font availability
 */
function isFontAvailable(fontName: string): boolean {
  if (typeof document === 'undefined') {
    return false; // Server-side rendering
  }

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  
  if (!context) return false;

  // Test string - using characters that vary significantly between fonts
  const testString = 'mmmmmmmmmmlli';
  const testSize = '72px';
  const fallbackFont = 'monospace';
  
  // Measure with fallback font
  context.font = `${testSize} ${fallbackFont}`;
  const fallbackWidth = context.measureText(testString).width;
  
  // Measure with target font (with fallback)
  context.font = `${testSize} "${fontName}", ${fallbackFont}`;
  const targetWidth = context.measureText(testString).width;
  
  // If widths are different, the font is available
  return Math.abs(targetWidth - fallbackWidth) > 1;
}

/**
 * Get all available system fonts
 * Returns a list of fonts that are actually available on the system
 */
export function getAvailableSystemFonts(): string[] {
  const availableFonts: string[] = [];
  
  // Check common system fonts
  for (const font of COMMON_SYSTEM_FONTS) {
    if (isFontAvailable(font)) {
      availableFonts.push(font);
    }
  }

  // Always include web-safe fonts (they have good fallbacks)
  availableFonts.push(...WEB_SAFE_FONTS);

  // Remove duplicates and sort
  return [...new Set(availableFonts)].sort();
}

/**
 * Get categorized fonts for better UX
 */
export interface FontCategory {
  name: string;
  fonts: string[];
}

export function getCategorizedFonts(): FontCategory[] {
  const availableFonts = getAvailableSystemFonts();
  
  const categories: FontCategory[] = [
    {
      name: "Recommended Fonts",
      fonts: availableFonts.filter(font => 
        font === 'Verdana' || 
        font === 'Noto Sans Arabic' ||
        font.includes('Noto Sans') ||
        font === 'Arabic Typesetting' ||
        font === 'Traditional Arabic'
      )
    },
    {
      name: "System Fonts",
      fonts: availableFonts.filter(font => 
        font.includes('SF Pro') || 
        font.includes('Helvetica') ||
        font === 'Arial' ||
        font === 'Tahoma'
      )
    },
    {
      name: "Arabic & Kurdish Fonts",
      fonts: availableFonts.filter(font =>
        font.includes('Arabic') ||
        font.includes('Noto Sans Arabic') ||
        font === 'Baghdad' ||
        font === 'Al Bayan' ||
        font === 'Traditional Arabic' ||
        font === 'Simplified Arabic'
      )
    },
    {
      name: "Modern Web Fonts",
      fonts: availableFonts.filter(font => 
        ['Inter', 'Roboto', 'Open Sans', 'Lato', 'Montserrat', 'Source Sans Pro', 'Raleway', 'Nunito', 'Poppins'].includes(font)
      )
    },
    {
      name: "Serif Fonts", 
      fonts: availableFonts.filter(font =>
        ['Georgia', 'Times New Roman', 'Times', 'Merriweather', 'Playfair Display'].includes(font)
      )
    },
    {
      name: "Monospace Fonts",
      fonts: availableFonts.filter(font =>
        ['Courier New', 'Monaco', 'Menlo', 'Consolas'].includes(font)
      )
    },
    {
      name: "Display Fonts",
      fonts: availableFonts.filter(font =>
        ['Impact', 'Arial Black', 'Trebuchet MS'].includes(font)
      )
    }
  ];

  // Filter out empty categories and add remaining fonts to "Other"
  const usedFonts = new Set(categories.flatMap(cat => cat.fonts));
  const otherFonts = availableFonts.filter(font => !usedFonts.has(font));
  
  if (otherFonts.length > 0) {
    categories.push({
      name: "Other Fonts",
      fonts: otherFonts
    });
  }

  return categories.filter(cat => cat.fonts.length > 0);
}

/**
 * Get font preview text based on font characteristics
 */
export function getFontPreviewText(fontName: string): string {
  const lowerFont = fontName.toLowerCase();
  
  if (lowerFont.includes('display') || lowerFont.includes('headline')) {
    return 'Display Heading';
  }
  
  if (lowerFont.includes('mono') || lowerFont.includes('code') || ['Monaco', 'Menlo', 'Courier New', 'Consolas'].includes(fontName)) {
    return 'Code Sample';
  }
  
  if (['Georgia', 'Times New Roman', 'Times', 'Merriweather'].includes(fontName)) {
    return 'Elegant serif text';
  }
  
  if (lowerFont.includes('condensed') || lowerFont.includes('narrow')) {
    return 'Condensed Text';
  }
  
  if (lowerFont.includes('rounded')) {
    return 'Friendly rounded text';
  }
  
  return 'Sample text';
}

/**
 * Validate that a font name is safe to use
 */
export function isValidFontName(fontName: string): boolean {
  // Check for basic font name validation
  if (!fontName || fontName.trim().length === 0) {
    return false;
  }
  
  // Prevent CSS injection attempts
  if (fontName.includes(';') || fontName.includes('{') || fontName.includes('}')) {
    return false;
  }
  
  return true;
}

/**
 * Get font-family CSS value with proper fallbacks
 */
export function getFontFamilyCSS(fontName: string): string {
  if (!isValidFontName(fontName)) {
    return 'system-ui, -apple-system, sans-serif';
  }
  
  // Fonts that need quotes in CSS
  const needsQuotes = fontName.includes(' ') || fontName.includes('-') || /^\d/.test(fontName);
  const quotedName = needsQuotes ? `"${fontName}"` : fontName;
  
  // Add appropriate fallbacks based on font type
  const lowerFont = fontName.toLowerCase();
  
  if (lowerFont.includes('mono') || ['Monaco', 'Menlo', 'Courier New', 'Consolas'].includes(fontName)) {
    return `${quotedName}, 'Monaco', 'Menlo', 'Courier New', monospace`;
  }
  
  if (['Georgia', 'Times New Roman', 'Times', 'Merriweather', 'Playfair Display'].includes(fontName)) {
    return `${quotedName}, 'Georgia', 'Times New Roman', serif`;
  }
  
  // Sans-serif fallback (most common case)
  return `${quotedName}, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`;
}

export { WEB_SAFE_FONTS, COMMON_SYSTEM_FONTS };