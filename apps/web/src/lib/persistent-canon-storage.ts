// Persistent Canon Storage System - Never lose your brand data
import { useEffect, useCallback, useRef } from 'react';

export interface CanonData {
  projectId: string;
  projectName: string;
  brandName: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    [key: string]: string;
  };
  fonts: {
    heading: string;
    body: string;
    [key: string]: string;
  };
  tone: string[];
  style: string[];
  guidelines: string;
  logos?: string[];
  assets?: any[];
  metadata: {
    createdAt: string;
    lastModified: string;
    version: number;
  };
}

class PersistentCanonStorage {
  private readonly STORAGE_KEY_PREFIX = 'nanodesigner_canon_';
  private readonly BACKUP_KEY_PREFIX = 'nanodesigner_canon_backup_';
  private readonly MASTER_INDEX_KEY = 'nanodesigner_canon_master_index';
  private autoSaveTimer: NodeJS.Timeout | null = null;
  private changeBuffer: Map<string, any> = new Map();

  // Initialize storage with multiple backup layers
  constructor() {
    this.initializeStorage();
    this.setupAutoBackup();
  }

  private initializeStorage(): void {
    // Ensure master index exists
    if (!localStorage.getItem(this.MASTER_INDEX_KEY)) {
      localStorage.setItem(this.MASTER_INDEX_KEY, JSON.stringify({
        projects: {},
        lastBackup: new Date().toISOString(),
        version: '1.0.0'
      }));
    }

    // Migrate old data if exists
    this.migrateOldData();
  }

  private migrateOldData(): void {
    // Check for any old canon data and migrate it
    const oldKeys = Object.keys(localStorage).filter(key => 
      key.includes('canon') && !key.startsWith(this.STORAGE_KEY_PREFIX)
    );

    oldKeys.forEach(oldKey => {
      const data = localStorage.getItem(oldKey);
      if (data) {
        try {
          const parsed = JSON.parse(data);
          const projectId = parsed.projectId || 'migrated_' + Date.now();
          this.saveCanon(projectId, parsed);
          console.log(`Migrated old canon data: ${oldKey}`);
        } catch (e) {
          console.error(`Failed to migrate ${oldKey}:`, e);
        }
      }
    });
  }

  // Save canon with multiple backup strategies
  public saveCanon(projectId: string, data: Partial<CanonData>): void {
    const storageKey = `${this.STORAGE_KEY_PREFIX}${projectId}`;
    const backupKey = `${this.BACKUP_KEY_PREFIX}${projectId}`;
    
    // Get existing data or create new
    const existingData = this.getCanon(projectId) || this.createDefaultCanon(projectId);
    
    // Merge with existing data (never delete, only add/update)
    const mergedData: CanonData = {
      ...existingData,
      ...data,
      metadata: {
        ...existingData.metadata,
        lastModified: new Date().toISOString(),
        version: (existingData.metadata?.version || 0) + 1
      }
    };

    try {
      // Save primary copy
      localStorage.setItem(storageKey, JSON.stringify(mergedData));
      
      // Save backup copy
      localStorage.setItem(backupKey, JSON.stringify(mergedData));
      
      // Save to IndexedDB as additional backup
      this.saveToIndexedDB(projectId, mergedData);
      
      // Update master index
      this.updateMasterIndex(projectId, mergedData);
      
      // Save to session storage as temporary backup
      sessionStorage.setItem(storageKey, JSON.stringify(mergedData));
      
      console.log(`✅ Canon saved successfully for project: ${projectId}`);
    } catch (e) {
      console.error('Failed to save canon:', e);
      // Try alternative storage methods
      this.saveToAlternativeStorage(projectId, mergedData);
    }
  }

  // Get canon with fallback strategies
  public getCanon(projectId: string): CanonData | null {
    const storageKey = `${this.STORAGE_KEY_PREFIX}${projectId}`;
    const backupKey = `${this.BACKUP_KEY_PREFIX}${projectId}`;
    
    // Try primary storage
    let data = localStorage.getItem(storageKey);
    
    // Try backup if primary fails
    if (!data) {
      data = localStorage.getItem(backupKey);
      if (data) {
        console.log('Restored from backup');
        // Restore primary from backup
        localStorage.setItem(storageKey, data);
      }
    }
    
    // Try session storage
    if (!data) {
      data = sessionStorage.getItem(storageKey);
      if (data) {
        console.log('Restored from session storage');
        // Restore to localStorage
        localStorage.setItem(storageKey, data);
      }
    }
    
    // Try IndexedDB
    if (!data) {
      return this.getFromIndexedDB(projectId);
    }
    
    try {
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Failed to parse canon data:', e);
      return null;
    }
  }

  // Auto-save functionality
  public enableAutoSave(projectId: string, getData: () => Partial<CanonData>): void {
    // Clear existing timer
    if (this.autoSaveTimer) {
      clearInterval(this.autoSaveTimer);
    }
    
    // Save immediately
    this.saveCanon(projectId, getData());
    
    // Set up auto-save every 5 seconds
    this.autoSaveTimer = setInterval(() => {
      const data = getData();
      if (data) {
        this.saveCanon(projectId, data);
      }
    }, 5000);
  }

  // Disable auto-save
  public disableAutoSave(): void {
    if (this.autoSaveTimer) {
      clearInterval(this.autoSaveTimer);
      this.autoSaveTimer = null;
    }
  }

  // Save to IndexedDB for additional persistence
  private async saveToIndexedDB(projectId: string, data: CanonData): Promise<void> {
    if (!window.indexedDB) return;
    
    try {
      const db = await this.openIndexedDB();
      const transaction = db.transaction(['canons'], 'readwrite');
      const store = transaction.objectStore('canons');
      
      await store.put({
        id: projectId,
        data: data,
        timestamp: Date.now()
      });
      
      db.close();
    } catch (e) {
      console.error('IndexedDB save failed:', e);
    }
  }

  // Get from IndexedDB
  private async getFromIndexedDB(projectId: string): Promise<CanonData | null> {
    if (!window.indexedDB) return null;
    
    try {
      const db = await this.openIndexedDB();
      const transaction = db.transaction(['canons'], 'readonly');
      const store = transaction.objectStore('canons');
      
      return new Promise((resolve) => {
        const request = store.get(projectId);
        request.onsuccess = () => {
          db.close();
          resolve(request.result?.data || null);
        };
        request.onerror = () => {
          db.close();
          resolve(null);
        };
      });
    } catch (e) {
      console.error('IndexedDB read failed:', e);
      return null;
    }
  }

  // Open IndexedDB connection
  private openIndexedDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('NanoDesignerCanons', 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains('canons')) {
          db.createObjectStore('canons', { keyPath: 'id' });
        }
      };
    });
  }

  // Alternative storage using cookies
  private saveToAlternativeStorage(projectId: string, data: CanonData): void {
    try {
      // Save critical data to cookie (limited size)
      const criticalData = {
        projectId: data.projectId,
        brandName: data.brandName,
        colors: data.colors,
        lastModified: data.metadata?.lastModified
      };
      
      document.cookie = `canon_${projectId}=${encodeURIComponent(JSON.stringify(criticalData))}; max-age=31536000; path=/`;
    } catch (e) {
      console.error('Alternative storage failed:', e);
    }
  }

  // Update master index
  private updateMasterIndex(projectId: string, data: CanonData): void {
    try {
      const indexData = JSON.parse(localStorage.getItem(this.MASTER_INDEX_KEY) || '{}');
      indexData.projects = indexData.projects || {};
      indexData.projects[projectId] = {
        name: data.projectName || data.brandName,
        lastModified: data.metadata?.lastModified,
        version: data.metadata?.version
      };
      indexData.lastBackup = new Date().toISOString();
      
      localStorage.setItem(this.MASTER_INDEX_KEY, JSON.stringify(indexData));
    } catch (e) {
      console.error('Failed to update master index:', e);
    }
  }

  // Set up automatic backup every hour
  private setupAutoBackup(): void {
    setInterval(() => {
      this.performFullBackup();
    }, 3600000); // Every hour
  }

  // Perform full backup of all canons
  private performFullBackup(): void {
    try {
      const allKeys = Object.keys(localStorage).filter(key => 
        key.startsWith(this.STORAGE_KEY_PREFIX)
      );
      
      const backupData = {
        timestamp: new Date().toISOString(),
        canons: {} as Record<string, any>
      };
      
      allKeys.forEach(key => {
        const data = localStorage.getItem(key);
        if (data) {
          backupData.canons[key] = JSON.parse(data);
        }
      });
      
      // Save full backup
      localStorage.setItem('nanodesigner_full_backup', JSON.stringify(backupData));
      
      console.log('Full backup completed');
    } catch (e) {
      console.error('Backup failed:', e);
    }
  }

  // Create default canon structure
  private createDefaultCanon(projectId: string): CanonData {
    return {
      projectId,
      projectName: 'Untitled Project',
      brandName: '',
      colors: {
        primary: '#003366',
        secondary: '#000000',
        accent: '#C0C0C0'
      },
      fonts: {
        heading: 'Arial',
        body: 'Arial'
      },
      tone: [],
      style: [],
      guidelines: '',
      metadata: {
        createdAt: new Date().toISOString(),
        lastModified: new Date().toISOString(),
        version: 1
      }
    };
  }

  // Get all saved canons
  public getAllCanons(): Record<string, CanonData> {
    const canons: Record<string, CanonData> = {};
    
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(this.STORAGE_KEY_PREFIX)) {
        const projectId = key.replace(this.STORAGE_KEY_PREFIX, '');
        const canon = this.getCanon(projectId);
        if (canon) {
          canons[projectId] = canon;
        }
      }
    });
    
    return canons;
  }

  // Export canon data
  public exportCanon(projectId: string): string {
    const canon = this.getCanon(projectId);
    return JSON.stringify(canon, null, 2);
  }

  // Import canon data
  public importCanon(projectId: string, jsonData: string): boolean {
    try {
      const data = JSON.parse(jsonData);
      this.saveCanon(projectId, data);
      return true;
    } catch (e) {
      console.error('Import failed:', e);
      return false;
    }
  }
}

// Singleton instance
export const canonStorage = new PersistentCanonStorage();

// React hook for auto-saving canon
export function useAutoSaveCanon(projectId: string, getCanonData: () => Partial<CanonData>) {
  const saveTimeoutRef = useRef<NodeJS.Timeout>();
  const lastSaveRef = useRef<string>('');

  const saveCanon = useCallback(() => {
    const data = getCanonData();
    const dataString = JSON.stringify(data);
    
    // Only save if data has changed
    if (dataString !== lastSaveRef.current) {
      canonStorage.saveCanon(projectId, data);
      lastSaveRef.current = dataString;
      console.log('Canon auto-saved');
    }
  }, [projectId, getCanonData]);

  // Debounced save
  const debouncedSave = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    saveTimeoutRef.current = setTimeout(() => {
      saveCanon();
    }, 1000); // Save 1 second after last change
  }, [saveCanon]);

  useEffect(() => {
    // Initial save
    saveCanon();
    
    // Set up periodic auto-save
    const interval = setInterval(saveCanon, 10000); // Every 10 seconds
    
    // Save on page unload
    const handleUnload = () => {
      saveCanon();
    };
    
    window.addEventListener('beforeunload', handleUnload);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('beforeunload', handleUnload);
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [saveCanon]);

  return {
    saveNow: saveCanon,
    debouncedSave,
    getSavedCanon: () => canonStorage.getCanon(projectId),
    exportCanon: () => canonStorage.exportCanon(projectId),
    importCanon: (data: string) => canonStorage.importCanon(projectId, data)
  };
}

export default canonStorage;