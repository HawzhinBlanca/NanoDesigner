import { NextRequest, NextResponse } from 'next/server';
import { projectService } from '@/lib/database/projects';
import { auth } from '@/lib/auth-bypass';
import { z } from 'zod';

// Input validation schemas
const CreateProjectSchema = z.object({
  name: z.string().min(1, 'Project name is required').max(255, 'Project name too long'),
  description: z.string().optional(),
  industry: z.string().optional(),
  brandGuidelines: z.string().optional(),
  organizationId: z.string().optional(),
});

const GetProjectsSchema = z.object({
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
});

// GET /api/projects - List user's projects with pagination
export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse and validate query parameters
    const { searchParams } = new URL(request.url);
    const queryParams = {
      page: searchParams.get('page'),
      limit: searchParams.get('limit'),
    };
    
    const { page, limit } = GetProjectsSchema.parse(queryParams);
    
    // Fetch projects with security and pagination
    const result = await projectService.getProjects(page, limit);
    
    return NextResponse.json({
      projects: result.projects,
      pagination: {
        page,
        limit,
        total: result.total,
        totalPages: Math.ceil(result.total / limit),
      }
    }, { status: 200 });
  } catch (error) {
    console.error('Error fetching projects:', error);
    
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { 
          error: 'Invalid query parameters',
          details: error.issues
        },
        { status: 400 }
      );
    }
    
    return NextResponse.json(
      { error: 'Failed to fetch projects' },
      { status: 500 }
    );
  }
}

// POST /api/projects - Create new project with security validation
export async function POST(request: NextRequest) {
  try {
    // Check authentication
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = CreateProjectSchema.parse(body);
    
    // Create project with security validation
    const project = await projectService.createProject(validatedData);
    
    return NextResponse.json({ project }, { status: 201 });
  } catch (error) {
    console.error('Error creating project:', error);
    
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
      if (error.message.includes('required') || error.message.includes('too long')) {
        return NextResponse.json(
          { error: error.message },
          { status: 400 }
        );
      }
    }
    
    return NextResponse.json(
      { error: 'Failed to create project' },
      { status: 500 }
    );
  }
}