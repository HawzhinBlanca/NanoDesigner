/**
 * Demo storage service using localStorage for persistence
 */

interface DemoProject {
  id: string;
  name: string;
  description: string;
  industry: string;
  brandGuidelines: string;
  status: 'draft' | 'active' | 'archived';
  createdAt: string;
  updatedAt: string;
  userId: string;
}

interface DemoAsset {
  id: string;
  projectId: string;
  fileName: string;
  storedFileName: string;
  fileSize: number;
  fileType: string;
  url: string;
  uploadedAt: string;
}

interface DemoGeneratedImage {
  id: string;
  projectId: string;
  prompt: string;
  imageUrl: string;
  createdAt: string;
}

const STORAGE_KEYS = {
  PROJECTS: 'nanodesigner_demo_projects',
  ASSETS: 'nanodesigner_demo_assets',
  IMAGES: 'nanodesigner_demo_images',
} as const;

class DemoStorage {
  private isClient() {
    return typeof window !== 'undefined';
  }

  // Projects
  saveProject(project: DemoProject): void {
    if (!this.isClient()) return;
    
    const projects = this.getProjects();
    const existingIndex = projects.findIndex(p => p.id === project.id);
    
    if (existingIndex >= 0) {
      projects[existingIndex] = { ...project, updatedAt: new Date().toISOString() };
    } else {
      projects.push(project);
    }
    
    localStorage.setItem(STORAGE_KEYS.PROJECTS, JSON.stringify(projects));
  }

  getProjects(): DemoProject[] {
    if (!this.isClient()) return this.getDefaultProjects();
    
    const stored = localStorage.getItem(STORAGE_KEYS.PROJECTS);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Error parsing stored projects:', e);
      }
    }
    
    // Return default projects if none stored
    const defaultProjects = this.getDefaultProjects();
    localStorage.setItem(STORAGE_KEYS.PROJECTS, JSON.stringify(defaultProjects));
    return defaultProjects;
  }

  getProject(id: string): DemoProject | null {
    const projects = this.getProjects();
    return projects.find(p => p.id === id) || null;
  }

  deleteProject(id: string): void {
    if (!this.isClient()) return;
    
    const projects = this.getProjects().filter(p => p.id !== id);
    localStorage.setItem(STORAGE_KEYS.PROJECTS, JSON.stringify(projects));
    
    // Also delete associated assets and images
    this.deleteAssetsByProject(id);
    this.deleteImagesByProject(id);
  }

  private getDefaultProjects(): DemoProject[] {
    return [
      {
        id: 'kaae',
        name: 'KAAE',
        description: 'KAAE Technology Company - Innovation & Trust',
        industry: 'Technology',
        brandGuidelines: 'Minimalist geometric design with deep blue (#003366), black, and silver accents. Professional, innovative, trustworthy brand identity with sharp lines and modern typography.',
        status: 'active',
        createdAt: '2025-09-11T10:00:00.000Z',
        updatedAt: '2025-09-11T11:00:00.000Z',
        userId: 'hawzhin',
      },
      {
        id: 'hawzhin-project',
        name: 'Hawzhin',
        description: 'Personal brand project for Hawzhin',
        industry: 'Technology / Personal Brand',
        brandGuidelines: 'Modern, professional, innovative tech aesthetic',
        status: 'active',
        createdAt: '2025-09-11T10:00:00.000Z',
        updatedAt: '2025-09-11T10:00:00.000Z',
        userId: 'hawzhin',
      },
      {
        id: '6b91653b-7504-4e5a-b426-697f9965a3db',
        name: 'Test E2E Project',
        description: 'Testing real project creation',
        industry: 'Technology',
        brandGuidelines: 'Modern and clean design',
        status: 'active',
        createdAt: '2025-09-07T20:02:43.586Z',
        updatedAt: '2025-09-08T10:29:22.335Z',
        userId: 'demo-user',
      },
      {
        id: 'demo-1',
        name: 'Demo Project 1',
        description: 'A sample project for demonstration',
        industry: 'Technology',
        brandGuidelines: 'Modern, clean design with blue accent colors',
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        userId: 'demo-user-123',
      },
      {
        id: 'demo-2',
        name: 'Demo Project 2',
        description: 'Another sample project',
        industry: 'Healthcare',
        brandGuidelines: 'Professional, trustworthy design with green accent colors',
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        userId: 'demo-user-123',
      }
    ];
  }

  // Assets
  saveAsset(asset: DemoAsset): void {
    if (!this.isClient()) return;
    
    const assets = this.getAssets();
    const existingIndex = assets.findIndex(a => a.id === asset.id);
    
    if (existingIndex >= 0) {
      assets[existingIndex] = asset;
    } else {
      assets.push(asset);
    }
    
    localStorage.setItem(STORAGE_KEYS.ASSETS, JSON.stringify(assets));
  }

  getAssets(): DemoAsset[] {
    if (!this.isClient()) return [];
    
    const stored = localStorage.getItem(STORAGE_KEYS.ASSETS);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Error parsing stored assets:', e);
      }
    }
    return [];
  }

  getAssetsByProject(projectId: string): DemoAsset[] {
    return this.getAssets().filter(a => a.projectId === projectId);
  }

  deleteAsset(id: string): void {
    if (!this.isClient()) return;
    
    const assets = this.getAssets().filter(a => a.id !== id);
    localStorage.setItem(STORAGE_KEYS.ASSETS, JSON.stringify(assets));
  }

  deleteAssetsByProject(projectId: string): void {
    if (!this.isClient()) return;
    
    const assets = this.getAssets().filter(a => a.projectId !== projectId);
    localStorage.setItem(STORAGE_KEYS.ASSETS, JSON.stringify(assets));
  }

  // Generated Images
  saveGeneratedImage(image: DemoGeneratedImage): void {
    if (!this.isClient()) return;
    
    const images = this.getGeneratedImages();
    const existingIndex = images.findIndex(i => i.id === image.id);
    
    if (existingIndex >= 0) {
      images[existingIndex] = image;
    } else {
      images.push(image);
    }
    
    localStorage.setItem(STORAGE_KEYS.IMAGES, JSON.stringify(images));
  }

  getGeneratedImages(): DemoGeneratedImage[] {
    if (!this.isClient()) return [];
    
    const stored = localStorage.getItem(STORAGE_KEYS.IMAGES);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Error parsing stored images:', e);
      }
    }
    return [];
  }

  getImagesByProject(projectId: string): DemoGeneratedImage[] {
    return this.getGeneratedImages().filter(i => i.projectId === projectId);
  }

  deleteGeneratedImage(id: string): void {
    if (!this.isClient()) return;
    
    const images = this.getGeneratedImages().filter(i => i.id !== id);
    localStorage.setItem(STORAGE_KEYS.IMAGES, JSON.stringify(images));
  }

  deleteImagesByProject(projectId: string): void {
    if (!this.isClient()) return;
    
    const images = this.getGeneratedImages().filter(i => i.projectId !== projectId);
    localStorage.setItem(STORAGE_KEYS.IMAGES, JSON.stringify(images));
  }

  // Clear all demo data
  clearAllData(): void {
    if (!this.isClient()) return;
    
    localStorage.removeItem(STORAGE_KEYS.PROJECTS);
    localStorage.removeItem(STORAGE_KEYS.ASSETS);
    localStorage.removeItem(STORAGE_KEYS.IMAGES);
  }
}

export const demoStorage = new DemoStorage();

// Export types for use in other files
export type { DemoProject, DemoAsset, DemoGeneratedImage };