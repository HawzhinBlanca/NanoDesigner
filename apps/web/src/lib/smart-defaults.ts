// Smart defaults and AI-powered suggestions system
import { useLocalStorage } from '@/hooks/use-local-storage';

// Smart default configurations
export interface SmartDefault {
  id: string;
  category: 'style' | 'dimensions' | 'colors' | 'prompt' | 'settings';
  value: any;
  confidence: number;
  reason: string;
}

// User preference learning
interface UserPreferences {
  favoriteStyles: string[];
  commonDimensions: { width: number; height: number; usage: number }[];
  colorPalettes: { colors: string[]; usage: number }[];
  promptPatterns: { pattern: string; usage: number }[];
  timeOfDayPreferences: Record<string, any>;
  projectTypePreferences: Record<string, any>;
}

// Smart suggestions engine
export class SmartDefaultsEngine {
  private preferences: UserPreferences;
  
  constructor(preferences: UserPreferences) {
    this.preferences = preferences;
  }
  
  // Get smart defaults based on context
  getSmartDefaults(context: {
    projectType?: string;
    timeOfDay?: string;
    previousPrompt?: string;
    userHistory?: any[];
  }): SmartDefault[] {
    const defaults: SmartDefault[] = [];
    
    // Style suggestions
    defaults.push(...this.getStyleSuggestions(context));
    
    // Dimension suggestions
    defaults.push(...this.getDimensionSuggestions(context));
    
    // Color suggestions
    defaults.push(...this.getColorSuggestions(context));
    
    // Prompt enhancements
    defaults.push(...this.getPromptSuggestions(context));
    
    return defaults.sort((a, b) => b.confidence - a.confidence);
  }
  
  // Style suggestions based on usage patterns
  private getStyleSuggestions(context: any): SmartDefault[] {
    const suggestions: SmartDefault[] = [];
    
    // Most used styles
    if (this.preferences.favoriteStyles.length > 0) {
      const topStyle = this.preferences.favoriteStyles[0];
      suggestions.push({
        id: 'style-favorite',
        category: 'style',
        value: topStyle,
        confidence: 0.9,
        reason: 'Your most frequently used style',
      });
    }
    
    // Time-based suggestions
    const hour = new Date().getHours();
    if (hour >= 6 && hour < 12) {
      suggestions.push({
        id: 'style-morning',
        category: 'style',
        value: 'bright and energetic',
        confidence: 0.7,
        reason: 'Morning designs tend to be brighter',
      });
    } else if (hour >= 18 || hour < 6) {
      suggestions.push({
        id: 'style-evening',
        category: 'style',
        value: 'calm and sophisticated',
        confidence: 0.7,
        reason: 'Evening designs often use calmer tones',
      });
    }
    
    return suggestions;
  }
  
  // Dimension suggestions based on common usage
  private getDimensionSuggestions(context: any): SmartDefault[] {
    const suggestions: SmartDefault[] = [];
    
    // Most used dimensions
    const sortedDimensions = this.preferences.commonDimensions
      .sort((a, b) => b.usage - a.usage);
    
    if (sortedDimensions.length > 0) {
      const top = sortedDimensions[0];
      suggestions.push({
        id: 'dim-common',
        category: 'dimensions',
        value: { width: top.width, height: top.height },
        confidence: 0.85,
        reason: `You've used ${top.width}x${top.height} ${top.usage} times`,
      });
    }
    
    // Context-based dimensions
    if (context.projectType === 'social-media') {
      suggestions.push({
        id: 'dim-social',
        category: 'dimensions',
        value: { width: 1080, height: 1080 },
        confidence: 0.8,
        reason: 'Optimal for social media posts',
      });
    } else if (context.projectType === 'presentation') {
      suggestions.push({
        id: 'dim-presentation',
        category: 'dimensions',
        value: { width: 1920, height: 1080 },
        confidence: 0.8,
        reason: 'Standard presentation format',
      });
    }
    
    return suggestions;
  }
  
  // Color palette suggestions
  private getColorSuggestions(context: any): SmartDefault[] {
    const suggestions: SmartDefault[] = [];
    
    // Most used palettes
    const sortedPalettes = this.preferences.colorPalettes
      .sort((a, b) => b.usage - a.usage);
    
    if (sortedPalettes.length > 0) {
      suggestions.push({
        id: 'colors-favorite',
        category: 'colors',
        value: sortedPalettes[0].colors,
        confidence: 0.85,
        reason: 'Your preferred color palette',
      });
    }
    
    // Seasonal colors
    const month = new Date().getMonth();
    if (month >= 2 && month <= 4) { // Spring
      suggestions.push({
        id: 'colors-spring',
        category: 'colors',
        value: ['#98FB98', '#FFB6C1', '#87CEEB'],
        confidence: 0.6,
        reason: 'Fresh spring colors',
      });
    } else if (month >= 5 && month <= 7) { // Summer
      suggestions.push({
        id: 'colors-summer',
        category: 'colors',
        value: ['#FFD700', '#00CED1', '#FF6347'],
        confidence: 0.6,
        reason: 'Vibrant summer palette',
      });
    } else if (month >= 8 && month <= 10) { // Fall
      suggestions.push({
        id: 'colors-fall',
        category: 'colors',
        value: ['#D2691E', '#FF8C00', '#8B4513'],
        confidence: 0.6,
        reason: 'Warm autumn tones',
      });
    } else { // Winter
      suggestions.push({
        id: 'colors-winter',
        category: 'colors',
        value: ['#4682B4', '#708090', '#F0F8FF'],
        confidence: 0.6,
        reason: 'Cool winter palette',
      });
    }
    
    return suggestions;
  }
  
  // Prompt enhancement suggestions
  private getPromptSuggestions(context: any): SmartDefault[] {
    const suggestions: SmartDefault[] = [];
    
    if (context.previousPrompt) {
      // Enhance with common patterns
      const enhancements = this.analyzePromptPatterns(context.previousPrompt);
      
      if (enhancements.length > 0) {
        suggestions.push({
          id: 'prompt-enhanced',
          category: 'prompt',
          value: enhancements.join(', '),
          confidence: 0.75,
          reason: 'Suggested enhancements based on successful patterns',
        });
      }
    }
    
    // Style keywords based on time
    const hour = new Date().getHours();
    const timeBasedKeywords = this.getTimeBasedKeywords(hour);
    
    if (timeBasedKeywords.length > 0) {
      suggestions.push({
        id: 'prompt-time',
        category: 'prompt',
        value: timeBasedKeywords,
        confidence: 0.6,
        reason: 'Keywords that work well at this time',
      });
    }
    
    return suggestions;
  }
  
  // Analyze prompt patterns for suggestions
  private analyzePromptPatterns(prompt: string): string[] {
    const enhancements: string[] = [];
    
    // Check for missing style descriptors
    if (!prompt.includes('style') && !prompt.includes('aesthetic')) {
      enhancements.push('modern style');
    }
    
    // Check for missing quality descriptors
    if (!prompt.includes('quality') && !prompt.includes('professional')) {
      enhancements.push('high quality');
    }
    
    // Check for missing mood descriptors
    if (!prompt.includes('mood') && !prompt.includes('feeling')) {
      enhancements.push('vibrant mood');
    }
    
    return enhancements;
  }
  
  // Get time-based keyword suggestions
  private getTimeBasedKeywords(hour: number): string[] {
    if (hour >= 6 && hour < 9) {
      return ['fresh', 'energetic', 'bright'];
    } else if (hour >= 9 && hour < 17) {
      return ['professional', 'clean', 'focused'];
    } else if (hour >= 17 && hour < 21) {
      return ['warm', 'relaxed', 'creative'];
    } else {
      return ['sophisticated', 'minimal', 'elegant'];
    }
  }
}

// React hook for smart defaults
export function useSmartDefaults() {
  const [preferences, setPreferences] = useLocalStorage<UserPreferences>('smartPreferences', {
    favoriteStyles: [],
    commonDimensions: [],
    colorPalettes: [],
    promptPatterns: [],
    timeOfDayPreferences: {},
    projectTypePreferences: {},
  });
  
  const engine = new SmartDefaultsEngine(preferences);
  
  // Learn from user actions
  const learnFromAction = (action: {
    type: 'style' | 'dimension' | 'color' | 'prompt';
    value: any;
  }) => {
    setPreferences(prev => {
      const updated = { ...prev };
      
      switch (action.type) {
        case 'style':
          if (!updated.favoriteStyles.includes(action.value)) {
            updated.favoriteStyles.push(action.value);
          }
          break;
          
        case 'dimension':
          const existing = updated.commonDimensions.find(
            d => d.width === action.value.width && d.height === action.value.height
          );
          if (existing) {
            existing.usage++;
          } else {
            updated.commonDimensions.push({
              ...action.value,
              usage: 1,
            });
          }
          break;
          
        case 'color':
          const paletteKey = action.value.join(',');
          const existingPalette = updated.colorPalettes.find(
            p => p.colors.join(',') === paletteKey
          );
          if (existingPalette) {
            existingPalette.usage++;
          } else {
            updated.colorPalettes.push({
              colors: action.value,
              usage: 1,
            });
          }
          break;
          
        case 'prompt':
          // Extract patterns from prompt
          const patterns = extractPatterns(action.value);
          patterns.forEach(pattern => {
            const existingPattern = updated.promptPatterns.find(
              p => p.pattern === pattern
            );
            if (existingPattern) {
              existingPattern.usage++;
            } else {
              updated.promptPatterns.push({
                pattern,
                usage: 1,
              });
            }
          });
          break;
      }
      
      return updated;
    });
  };
  
  // Get suggestions for current context
  const getSuggestions = (context: any = {}) => {
    return engine.getSmartDefaults(context);
  };
  
  // Reset learning data
  const resetLearning = () => {
    setPreferences({
      favoriteStyles: [],
      commonDimensions: [],
      colorPalettes: [],
      promptPatterns: [],
      timeOfDayPreferences: {},
      projectTypePreferences: {},
    });
  };
  
  return {
    preferences,
    learnFromAction,
    getSuggestions,
    resetLearning,
  };
}

// Pattern extraction from prompts
function extractPatterns(prompt: string): string[] {
  const patterns: string[] = [];
  
  // Extract style patterns
  const styleMatch = prompt.match(/(modern|classic|minimal|bold|elegant|playful)\s+\w+/gi);
  if (styleMatch) patterns.push(...styleMatch);
  
  // Extract quality patterns
  const qualityMatch = prompt.match(/(high quality|professional|polished|refined)/gi);
  if (qualityMatch) patterns.push(...qualityMatch);
  
  // Extract color patterns
  const colorMatch = prompt.match(/(vibrant|muted|pastel|monochrome|colorful)/gi);
  if (colorMatch) patterns.push(...colorMatch);
  
  return patterns;
}

// Preset suggestions
export const presetSuggestions = {
  prompts: [
    'Modern minimalist logo with geometric shapes',
    'Vibrant abstract pattern with organic forms',
    'Professional business card with clean typography',
    'Social media banner with bold colors',
    'Elegant invitation with floral elements',
  ],
  styles: [
    { name: 'Clean & Minimal', keywords: ['minimal', 'clean', 'simple', 'white space'] },
    { name: 'Bold & Playful', keywords: ['bold', 'playful', 'colorful', 'dynamic'] },
    { name: 'Elegant & Sophisticated', keywords: ['elegant', 'sophisticated', 'refined', 'luxury'] },
    { name: 'Retro & Vintage', keywords: ['retro', 'vintage', 'nostalgic', 'classic'] },
    { name: 'Modern & Tech', keywords: ['modern', 'tech', 'futuristic', 'digital'] },
  ],
  dimensions: [
    { name: 'Instagram Post', width: 1080, height: 1080 },
    { name: 'Twitter Header', width: 1500, height: 500 },
    { name: 'LinkedIn Banner', width: 1584, height: 396 },
    { name: 'Facebook Cover', width: 820, height: 312 },
    { name: 'Business Card', width: 1050, height: 600 },
    { name: 'Presentation', width: 1920, height: 1080 },
    { name: 'Phone Wallpaper', width: 1080, height: 1920 },
    { name: 'Desktop Wallpaper', width: 2560, height: 1440 },
  ],
  palettes: [
    { name: 'Ocean', colors: ['#0066CC', '#00AAE4', '#00D4FF', '#E6F7FF'] },
    { name: 'Sunset', colors: ['#FF6B6B', '#FFA500', '#FFD700', '#FFF3E0'] },
    { name: 'Forest', colors: ['#228B22', '#90EE90', '#F0E68C', '#8FBC8F'] },
    { name: 'Monochrome', colors: ['#000000', '#666666', '#CCCCCC', '#FFFFFF'] },
    { name: 'Pastel', colors: ['#FFB3BA', '#BAFFC9', '#BAE1FF', '#FFFFBA'] },
  ],
};