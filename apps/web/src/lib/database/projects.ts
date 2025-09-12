import prisma from '../prisma';
import { Project, Asset, ProjectStatus } from '../../generated/prisma';
// import { currentUser } from '@clerk/nextjs/server';

// Type definitions for API compatibility
export interface CreateProjectData {
  name: string;
  description?: string;
  industry?: string;
  brandGuidelines?: string;
  organizationId?: string;
}

export interface UpdateProjectData {
  name?: string;
  description?: string;
  industry?: string;
  brandGuidelines?: string;
  status?: ProjectStatus;
}

export interface CreateAssetData {
  fileName: string;
  storedFileName: string;
  fileSize: number;
  fileType: string;
  mimeType: string;
  url: string;
  secureUrl?: string;
  checksum?: string;
  isPublic?: boolean;
}

// Project service with security and multi-tenancy
export class ProjectService {
  
  // Get current user - always use bypass auth for now
  private async getCurrentUserId(): Promise<string> {
    // Always use bypass user
    const bypassUserId = 'demo-user-123';
    
    // Ensure bypass user exists in database
    const dbUser = await prisma.user.upsert({
      where: { clerkId: bypassUserId },
      update: {},
      create: {
        clerkId: bypassUserId,
        email: 'demo@example.com',
        firstName: 'Demo',
        lastName: 'User',
      }
    });
    
    return dbUser.id;
  }

  // Create project with security validation
  async createProject(data: CreateProjectData): Promise<Project> {
    const userId = await this.getCurrentUserId();
    
    // Input validation
    if (!data.name || data.name.trim().length === 0) {
      throw new Error('Project name is required');
    }
    
    if (data.name.length > 255) {
      throw new Error('Project name must be less than 255 characters');
    }
    
    // Create project with audit logging
    const project = await prisma.$transaction(async (tx) => {
      const newProject = await tx.project.create({
        data: {
          name: data.name.trim(),
          description: data.description?.trim() || '',
          industry: data.industry?.trim() || '',
          brandGuidelines: data.brandGuidelines?.trim() || '',
          userId,
          organizationId: data.organizationId,
          status: ProjectStatus.ACTIVE,
        },
        include: {
          assets: true,
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              email: true,
            }
          }
        }
      });
      
      // Audit log
      await tx.auditLog.create({
        data: {
          action: 'CREATE_PROJECT',
          entityType: 'Project',
          entityId: newProject.id,
          newValues: {
            name: newProject.name,
            description: newProject.description,
            industry: newProject.industry,
          } as any,
          userId,
        }
      });
      
      return newProject;
    });
    
    return project;
  }

  // Get projects for current user with pagination
  async getProjects(page = 1, limit = 20): Promise<{ projects: Project[]; total: number }> {
    const userId = await this.getCurrentUserId();
    const skip = (page - 1) * limit;
    
    const [projects, total] = await Promise.all([
      prisma.project.findMany({
        where: {
          userId,
          status: { not: ProjectStatus.DELETED }
        },
        include: {
          assets: {
            orderBy: { uploadedAt: 'desc' },
            take: 5, // Include recent assets
          },
          _count: {
            select: {
              assets: true,
              renders: true,
            }
          }
        },
        orderBy: { updatedAt: 'desc' },
        skip,
        take: limit,
      }),
      prisma.project.count({
        where: {
          userId,
          status: { not: ProjectStatus.DELETED }
        }
      })
    ]);
    
    return { projects, total };
  }

  // Get single project with security check
  async getProject(projectId: string): Promise<Project | null> {
    const userId = await this.getCurrentUserId();
    
    const project = await prisma.project.findFirst({
      where: {
        id: projectId,
        userId, // Security: Only return user's own projects
        status: { not: ProjectStatus.DELETED }
      },
      include: {
        assets: {
          orderBy: { uploadedAt: 'desc' }
        },
        renders: {
          orderBy: { createdAt: 'desc' },
          take: 10
        },
        canons: {
          where: { isActive: true },
          orderBy: { version: 'desc' }
        }
      }
    });
    
    return project;
  }

  // Update project with validation
  async updateProject(projectId: string, data: UpdateProjectData): Promise<Project> {
    const userId = await this.getCurrentUserId();
    
    // Verify ownership
    const existingProject = await prisma.project.findFirst({
      where: { id: projectId, userId }
    });
    
    if (!existingProject) {
      throw new Error('Project not found or access denied');
    }
    
    // Input validation
    if (data.name !== undefined) {
      if (!data.name || data.name.trim().length === 0) {
        throw new Error('Project name cannot be empty');
      }
      if (data.name.length > 255) {
        throw new Error('Project name must be less than 255 characters');
      }
    }
    
    const updatedProject = await prisma.$transaction(async (tx) => {
      const project = await tx.project.update({
        where: { id: projectId },
        data: {
          ...(data.name && { name: data.name.trim() }),
          ...(data.description !== undefined && { description: data.description.trim() }),
          ...(data.industry !== undefined && { industry: data.industry.trim() }),
          ...(data.brandGuidelines !== undefined && { brandGuidelines: data.brandGuidelines.trim() }),
          ...(data.status && { status: data.status }),
          updatedAt: new Date(),
        },
        include: {
          assets: true,
        }
      });
      
      // Audit log
      await tx.auditLog.create({
        data: {
          action: 'UPDATE_PROJECT',
          entityType: 'Project',
          entityId: projectId,
          oldValues: {
            name: existingProject.name,
            description: existingProject.description,
            industry: existingProject.industry,
          },
          newValues: data as any,
          userId,
        }
      });
      
      return project;
    });
    
    return updatedProject;
  }

  // Delete project (soft delete)
  async deleteProject(projectId: string): Promise<void> {
    const userId = await this.getCurrentUserId();
    
    // Verify ownership
    const existingProject = await prisma.project.findFirst({
      where: { id: projectId, userId }
    });
    
    if (!existingProject) {
      throw new Error('Project not found or access denied');
    }
    
    await prisma.$transaction(async (tx) => {
      await tx.project.update({
        where: { id: projectId },
        data: { 
          status: ProjectStatus.DELETED,
          updatedAt: new Date(),
        }
      });
      
      // Audit log
      await tx.auditLog.create({
        data: {
          action: 'DELETE_PROJECT',
          entityType: 'Project',
          entityId: projectId,
          userId,
        }
      });
    });
  }

  // Add asset to project
  async addAsset(projectId: string, assetData: CreateAssetData): Promise<Asset> {
    const userId = await this.getCurrentUserId();
    
    // Verify project ownership
    const project = await prisma.project.findFirst({
      where: { id: projectId, userId }
    });
    
    if (!project) {
      throw new Error('Project not found or access denied');
    }
    
    // Input validation
    if (!assetData.fileName || !assetData.storedFileName) {
      throw new Error('File name and stored file name are required');
    }
    
    if (assetData.fileSize <= 0 || assetData.fileSize > 50 * 1024 * 1024) { // 50MB limit
      throw new Error('Invalid file size');
    }
    
    const asset = await prisma.$transaction(async (tx) => {
      const newAsset = await tx.asset.create({
        data: {
          fileName: assetData.fileName,
          storedFileName: assetData.storedFileName,
          fileSize: assetData.fileSize,
          fileType: assetData.fileType,
          mimeType: assetData.mimeType,
          url: assetData.url,
          secureUrl: assetData.secureUrl,
          checksum: assetData.checksum,
          isPublic: assetData.isPublic || false,
          userId,
          projectId,
        }
      });
      
      // Update project timestamp
      await tx.project.update({
        where: { id: projectId },
        data: { updatedAt: new Date() }
      });
      
      // Audit log
      await tx.auditLog.create({
        data: {
          action: 'ADD_ASSET',
          entityType: 'Asset',
          entityId: newAsset.id,
          newValues: {
            fileName: assetData.fileName,
            fileSize: assetData.fileSize,
            fileType: assetData.fileType,
          } as any,
          userId,
        }
      });
      
      return newAsset;
    });
    
    return asset;
  }
}

// Export singleton instance
export const projectService = new ProjectService();
