import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

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
          })),
        
        removeEvidence: (item) =>
          set((state) => ({
            evidenceItems: state.evidenceItems.filter((e) => e !== item),
          })),
        
        extractFromEvidence: async () => {
          set({ extracting: true, error: null });
          try {
            // TODO: Call API to extract brand elements from evidence
            await new Promise((resolve) => setTimeout(resolve, 2000));
            set({ extracting: false });
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
            // TODO: Save to API
            await new Promise((resolve) => setTimeout(resolve, 1500));
            set({ isSaving: false, isDirty: false });
          } catch (error) {
            set({ isSaving: false, error: String(error) });
          }
        },
        
        load: async (canonId) => {
          set({ isLoading: true, error: null });
          try {
            // TODO: Load from API
            await new Promise((resolve) => setTimeout(resolve, 1000));
            set({ isLoading: false });
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