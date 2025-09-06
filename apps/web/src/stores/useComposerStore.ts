import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { RenderRequest, RenderResponse, JobStatusResponse } from "@/lib/api";

interface Variant {
  id: string;
  prompt: string;
  constraints?: any;
  previewUrl?: string;
  finalUrl?: string;
  status: "idle" | "generating" | "completed" | "failed";
  error?: string;
}

interface ComposerState {
  // Current composition
  prompt: string;
  constraints: {
    palette?: string[];
    fonts?: string[];
    logoSafeZone?: { x: number; y: number; width: number; height: number };
  };
  references: string[];
  format: string;
  dimensions: string;
  
  // Variants
  variants: Variant[];
  selectedVariantId: string | null;
  comparing: string[];
  
  // Generation state
  isGenerating: boolean;
  currentJobId: string | null;
  progress: number;
  
  // Actions
  setPrompt: (prompt: string) => void;
  setConstraints: (constraints: any) => void;
  addReference: (url: string) => void;
  removeReference: (url: string) => void;
  setFormat: (format: string) => void;
  setDimensions: (dimensions: string) => void;
  
  // Variant actions
  generateVariants: (count: number) => void;
  selectVariant: (id: string) => void;
  compareVariants: (ids: string[]) => void;
  updateVariant: (id: string, updates: Partial<Variant>) => void;
  removeVariant: (id: string) => void;
  
  // Generation actions
  setGenerating: (isGenerating: boolean) => void;
  setJobId: (jobId: string | null) => void;
  setProgress: (progress: number) => void;
  
  // Utility
  reset: () => void;
}

export const useComposerStore = create<ComposerState>()(
  devtools(
    (set, get) => ({
      // Initial state
      prompt: "",
      constraints: {},
      references: [],
      format: "png",
      dimensions: "1920x1080",
      variants: [],
      selectedVariantId: null,
      comparing: [],
      isGenerating: false,
      currentJobId: null,
      progress: 0,

      // Actions
      setPrompt: (prompt) => set({ prompt }),
      
      setConstraints: (constraints) => set({ constraints }),
      
      addReference: (url) =>
        set((state) => ({ references: [...state.references, url] })),
      
      removeReference: (url) =>
        set((state) => ({
          references: state.references.filter((r) => r !== url),
        })),
      
      setFormat: (format) => set({ format }),
      
      setDimensions: (dimensions) => set({ dimensions }),
      
      generateVariants: (count) => {
        const newVariants: Variant[] = [];
        for (let i = 0; i < count; i++) {
          newVariants.push({
            id: `variant-${Date.now()}-${i}`,
            prompt: get().prompt,
            constraints: get().constraints,
            status: "idle",
          });
        }
        set((state) => ({ variants: [...state.variants, ...newVariants] }));
      },
      
      selectVariant: (id) => set({ selectedVariantId: id }),
      
      compareVariants: (ids) => set({ comparing: ids }),
      
      updateVariant: (id, updates) =>
        set((state) => ({
          variants: state.variants.map((v) =>
            v.id === id ? { ...v, ...updates } : v
          ),
        })),
      
      removeVariant: (id) =>
        set((state) => ({
          variants: state.variants.filter((v) => v.id !== id),
          selectedVariantId:
            state.selectedVariantId === id ? null : state.selectedVariantId,
          comparing: state.comparing.filter((cId) => cId !== id),
        })),
      
      setGenerating: (isGenerating) => set({ isGenerating }),
      
      setJobId: (currentJobId) => set({ currentJobId }),
      
      setProgress: (progress) => set({ progress }),
      
      reset: () =>
        set({
          prompt: "",
          constraints: {},
          references: [],
          format: "png",
          dimensions: "1920x1080",
          variants: [],
          selectedVariantId: null,
          comparing: [],
          isGenerating: false,
          currentJobId: null,
          progress: 0,
        }),
    })
  )
);