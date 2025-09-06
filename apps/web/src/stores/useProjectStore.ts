import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
  settings: {
    defaultFormat: string;
    defaultDimensions: string;
    brandCanonId?: string;
  };
}

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    persist(
      (set) => ({
        projects: [],
        currentProject: null,
        loading: false,
        error: null,

        setProjects: (projects) => set({ projects }),
        
        setCurrentProject: (project) => set({ currentProject: project }),
        
        addProject: (project) =>
          set((state) => ({ projects: [...state.projects, project] })),
        
        updateProject: (id, updates) =>
          set((state) => ({
            projects: state.projects.map((p) =>
              p.id === id ? { ...p, ...updates } : p
            ),
            currentProject:
              state.currentProject?.id === id
                ? { ...state.currentProject, ...updates }
                : state.currentProject,
          })),
        
        deleteProject: (id) =>
          set((state) => ({
            projects: state.projects.filter((p) => p.id !== id),
            currentProject:
              state.currentProject?.id === id ? null : state.currentProject,
          })),
        
        setLoading: (loading) => set({ loading }),
        
        setError: (error) => set({ error }),
      }),
      {
        name: "project-store",
      }
    )
  )
);