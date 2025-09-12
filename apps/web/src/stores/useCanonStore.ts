import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  neutral: string[];
  custom: string[];
}

interface Typography {
  headingFont: string;
  bodyFont: string;
  displayFont?: string;
  fonts: string[]; // Available font palette
  sizes: {
    h1: string;
    h2: string;
    h3: string;
    body: string;
    small: string;
  };
}

interface VoiceAndTone {
  personality: string[];
  tone: "formal" | "casual" | "playful" | "serious" | "professional";
  keywords: string[];
  avoidWords: string[];
}

interface BrandCanon {
  id: string;
  projectId: string;
  name: string;
  version: number;
  palette: ColorPalette;
  typography: Typography;
  voice: VoiceAndTone;
  logos: string[];
  guidelines: string;
  createdAt: Date;
  updatedAt: Date;
}

interface CanonHistory {
  id: string;
  canonId: string;
  version: number;
  changes: string;
  timestamp: Date;
  userId: string;
}

interface CanonState {
  currentCanon: BrandCanon | null;
  history: CanonHistory[];
  isDirty: boolean;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  
  // Evidence
  evidenceItems: string[];
  extracting: boolean;
  
  // Actions
  setCanon: (canon: BrandCanon) => void;
  updatePalette: (palette: Partial<ColorPalette>) => void;
  updateTypography: (typography: Partial<Typography>) => void;
  updateVoice: (voice: Partial<VoiceAndTone>) => void;
  addLogo: (logoUrl: string) => void;
  removeLogo: (logoUrl: string) => void;
  setGuidelines: (guidelines: string) => void;
  
  // Evidence actions
  addEvidence: (items: string[]) => void;
  removeEvidence: (item: string) => void;
  extractFromEvidence: () => Promise<void>;
  
  // History actions
  loadHistory: (canonId: string) => Promise<void>;
  revertToVersion: (version: number) => Promise<void>;
  
  // Save/Load
  save: () => Promise<void>;
  load: (canonId: string) => Promise<void>;
  setDirty: (isDirty: boolean) => void;
  setError: (error: string | null) => void;
}

export const useCanonStore = create<CanonState>()(
  devtools(
    persist(
      (set, get) => ({
        currentCanon: null,
        history: [],
        isDirty: false,
        isLoading: false,
        isSaving: false,
        error: null,
        evidenceItems: [],
        extracting: false,

        setCanon: (canon) => set({ currentCanon: canon, isDirty: false }),
        
        updatePalette: (palette) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? {
                  ...state.currentCanon,
                  palette: { ...state.currentCanon.palette, ...palette },
                }
              : null,
            isDirty: true,
          })),
        
        updateTypography: (typography) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? {
                  ...state.currentCanon,
                  typography: { ...state.currentCanon.typography, ...typography },
                }
              : null,
            isDirty: true,
          })),
        
        updateVoice: (voice) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? {
                  ...state.currentCanon,
                  voice: { ...state.currentCanon.voice, ...voice },
                }
              : null,
            isDirty: true,
          })),
        
        addLogo: (logoUrl) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? {
                  ...state.currentCanon,
                  logos: [...state.currentCanon.logos, logoUrl],
                }
              : null,
            isDirty: true,
          })),
        
        removeLogo: (logoUrl) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? {
                  ...state.currentCanon,
                  logos: state.currentCanon.logos.filter((l) => l !== logoUrl),
                }
              : null,
            isDirty: true,
          })),
        
        setGuidelines: (guidelines) =>
          set((state) => ({
            currentCanon: state.currentCanon
              ? { ...state.currentCanon, guidelines }
              : null,
            isDirty: true,
          })),
        
        addEvidence: (items) =>
          set((state) => ({
            evidenceItems: [...state.evidenceItems, ...items],
            isDirty: true,
          })),
        
        removeEvidence: (item) =>
          set((state) => ({
            evidenceItems: state.evidenceItems.filter((e) => e !== item),
            isDirty: true,
          })),
        
        extractFromEvidence: async () => {
          set({ extracting: true, error: null });
          try {
            const state = get();
            if (!state.currentCanon?.projectId) {
              throw new Error("No project ID available for evidence extraction");
            }

            // Call Canon derive API
            const response = await fetch(`${API_BASE_URL}/canon/derive`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                project_id: state.currentCanon.projectId,
                evidence_ids: state.evidenceItems
              })
            });

            if (!response.ok) {
              throw new Error(`API error: ${response.status}`);
            }

            const canonData = await response.json();
            
            // Update current canon with extracted data
            set((state) => ({
              currentCanon: state.currentCanon ? {
                ...state.currentCanon,
                palette: {
                  ...state.currentCanon.palette,
                  primary: canonData.palette_hex[0] || state.currentCanon.palette.primary,
                  secondary: canonData.palette_hex[1] || state.currentCanon.palette.secondary,
                  accent: canonData.palette_hex[2] || state.currentCanon.palette.accent,
                  custom: canonData.palette_hex || state.currentCanon.palette.custom
                },
                typography: {
                  ...state.currentCanon.typography,
                  fonts: canonData.fonts || state.currentCanon.typography.fonts
                },
                voice: {
                  ...state.currentCanon.voice,
                  tone: canonData.voice?.tone || state.currentCanon.voice.tone,
                  keywords: canonData.voice?.dos || state.currentCanon.voice.keywords,
                  avoidWords: canonData.voice?.donts || state.currentCanon.voice.avoidWords
                },
                updatedAt: new Date()
              } : null,
              extracting: false,
              isDirty: true
            }));
          } catch (error) {
            set({ extracting: false, error: String(error) });
          }
        },
        
        loadHistory: async (canonId) => {
          set({ isLoading: true });
          try {
            // TODO: Load history from API
            await new Promise((resolve) => setTimeout(resolve, 1000));
            set({ history: [], isLoading: false });
          } catch (error) {
            set({ isLoading: false, error: String(error) });
          }
        },
        
        revertToVersion: async (version) => {
          set({ isLoading: true });
          try {
            // TODO: Load specific version from API
            await new Promise((resolve) => setTimeout(resolve, 1000));
            set({ isLoading: false });
          } catch (error) {
            set({ isLoading: false, error: String(error) });
          }
        },
        
        save: async () => {
          set({ isSaving: true, error: null });
          try {
            const state = get();
            if (!state.currentCanon) {
              throw new Error("No canon data to save");
            }

            // Prepare data for backend API
            const saveData = {
              palette_hex: [
                state.currentCanon.palette.primary,
                state.currentCanon.palette.secondary,
                state.currentCanon.palette.accent,
                ...state.currentCanon.palette.custom
              ].filter(Boolean),
              fonts: state.currentCanon.typography.fonts,
              voice: {
                tone: state.currentCanon.voice.tone,
                dos: state.currentCanon.voice.keywords,
                donts: state.currentCanon.voice.avoidWords
              }
            };

            // Call Canon save API
            const response = await fetch(`${API_BASE_URL}/canon/${state.currentCanon.projectId}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(saveData)
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
              throw new Error(errorData.detail || `API error: ${response.status}`);
            }

            // Update timestamp and version
            const updatedCanon = {
              ...state.currentCanon,
              updatedAt: new Date(),
              version: state.currentCanon.version + 1,
            };
            
            set({ 
              currentCanon: updatedCanon,
              isSaving: false, 
              isDirty: false 
            });
          } catch (error) {
            set({ isSaving: false, error: String(error) });
          }
        },
        
        load: async (projectId) => {
          set({ isLoading: true, error: null });
          try {
            // Call Canon get API
            const response = await fetch(`${API_BASE_URL}/canon/${projectId}`, {
              method: 'GET',
              headers: {
                'Content-Type': 'application/json',
              }
            });

            if (!response.ok) {
              if (response.status === 404) {
                // No canon found, use defaults
                set({ isLoading: false, currentCanon: null });
                return;
              }
              throw new Error(`API error: ${response.status}`);
            }

            const canonData = await response.json();
            
            // Transform API response to internal format
            const loadedCanon: BrandCanon = {
              id: `canon_${projectId}`,
              projectId: projectId,
              name: `${projectId} Brand Canon`,
              version: 1,
              palette: {
                primary: canonData.palette_hex?.[0] || '#000000',
                secondary: canonData.palette_hex?.[1] || '#FFFFFF',
                accent: canonData.palette_hex?.[2] || '#007bff',
                neutral: ['#f8f9fa', '#e9ecef', '#dee2e6'],
                custom: canonData.palette_hex?.slice(3) || []
              },
              typography: {
                headingFont: canonData.fonts?.[0] || 'Helvetica',
                bodyFont: canonData.fonts?.[1] || 'Arial',
                fonts: canonData.fonts || ['Helvetica', 'Arial'],
                sizes: {
                  h1: '2rem',
                  h2: '1.75rem',
                  h3: '1.5rem',
                  body: '1rem',
                  small: '0.875rem'
                }
              },
              voice: {
                personality: ['professional', 'modern'],
                tone: (canonData.voice?.tone as any) || 'professional',
                keywords: canonData.voice?.dos || [],
                avoidWords: canonData.voice?.donts || []
              },
              logos: [],
              guidelines: 'Auto-generated brand canon',
              createdAt: new Date(),
              updatedAt: new Date()
            };

            set({ 
              currentCanon: loadedCanon,
              isLoading: false,
              isDirty: false
            });
          } catch (error) {
            set({ isLoading: false, error: String(error) });
          }
        },
        
        setDirty: (isDirty) => set({ isDirty }),
        
        setError: (error) => set({ error }),
      }),
      {
        name: "canon-store",
        partialize: (state) => ({ currentCanon: state.currentCanon }),
      }
    )
  )
);