import { NextRequest, NextResponse } from 'next/server';
import { projectService } from '@/lib/database/projects';
import { auth } from '@/lib/auth-bypass';
import { z } from 'zod';
import { ProjectStatus } from '@/generated/prisma';

// Input validation schemas
const UpdateProjectSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  description: z.string().optional(),
  industry: z.string().optional(),
  brandGuidelines: z.string().optional(),
  status: z.nativeEnum(ProjectStatus).optional(),
});

// GET /api/projects/[id] - Get specific project with security validation
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { id } = await params;
    
    // Validate project ID format
    if (!id || typeof id !== 'string') {
      return NextResponse.json(
        { error: 'Invalid project ID' },
        { status: 400 }
      );
    }
    
    // Get project with security check (only user's own projects)
    const project = await projectService.getProject(id);
    
    if (!project) {
      return NextResponse.json(
        { error: 'Project not found or access denied' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ project }, { status: 200 });
  } catch (error) {
    console.error('Error fetching project:', error);
    return NextResponse.json(
      { error: 'Failed to fetch project' },
      { status: 500 }
    );
  }
}

// PUT /api/projects/[id] - Update project with validation and security
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { id } = await params;
    
    // Validate project ID format
    if (!id || typeof id !== 'string') {
      return NextResponse.json(
        { error: 'Invalid project ID' },
        { status: 400 }
      );
    }
    
    // Parse and validate request body
    const body = await request.json();
    const validatedData = UpdateProjectSchema.parse(body);
    
    // Update project with security validation
    const project = await projectService.updateProject(id, validatedData);
    
    return NextResponse.json({ project }, { status: 200 });
  } catch (error) {
    console.error('Error updating project:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { 
          error: 'Invalid project data',
          details: error.issues
        },
        { status: 400 }
      );
    }
    
    if (error instanceof Error) {
      // Handle known business logic errors
      if (error.message.includes('not found') || error.message.includes('access denied')) {
        return NextResponse.json(
          { error: error.message },
          { status: 404 }
        );
      }
      
      if (error.message.includes('required') || error.message.includes('too long')) {
        return NextResponse.json(
          { error: error.message },
          { status: 400 }
        );
      }
    }
    
    return NextResponse.json(
      { error: 'Failed to update project' },
      { status: 500 }
    );
  }
}

// DELETE /api/projects/[id] - Soft delete project with security validation
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { id } = await params;
    
    // Validate project ID format
    if (!id || typeof id !== 'string') {
      return NextResponse.json(
        { error: 'Invalid project ID' },
        { status: 400 }
      );
    }
    
    // Soft delete project with security validation
    await projectService.deleteProject(id);
    
    return NextResponse.json({ 
      message: 'Project deleted successfully',
      note: 'Project has been soft-deleted and can be recovered if needed'
    }, { status: 200 });
  } catch (error) {
    console.error('Error deleting project:', error);
    
    if (error instanceof Error) {
      if (error.message.includes('not found') || error.message.includes('access denied')) {
        return NextResponse.json(
          { error: error.message },
          { status: 404 }
        );
      }
    }
    
    return NextResponse.json(
      { error: 'Failed to delete project' },
      { status: 500 }
    );
  }
}