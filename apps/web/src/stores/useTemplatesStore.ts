import { create } from "zustand";
import { devtools } from "zustand/middleware";

export interface TemplateItem {
  id: string;
  name: string;
  prompt: string;
  constraints?: {
    palette?: string[];
    fonts?: string[];
    logoSafeZone?: { x: number; y: number; width: number; height: number };
  };
  createdAt: number;
}

interface TemplatesState {
  items: TemplateItem[];
  add: (t: Omit<TemplateItem, "id" | "createdAt">) => void;
  update: (id: string, u: Partial<TemplateItem>) => void;
  remove: (id: string) => void;
}

export const useTemplatesStore = create<TemplatesState>()(
  devtools((set) => ({
    items: [],
    add: (t) =>
      set((s) => ({ items: [...s.items, { ...t, id: crypto.randomUUID(), createdAt: Date.now() }] })),
    update: (id, u) =>
      set((s) => ({ items: s.items.map((it) => (it.id === id ? { ...it, ...u } : it)) })),
    remove: (id) => set((s) => ({ items: s.items.filter((it) => it.id !== id) })),
  }))
);

