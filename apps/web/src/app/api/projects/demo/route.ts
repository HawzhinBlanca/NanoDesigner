import { NextRequest, NextResponse } from 'next/server';

// Demo API endpoints that work without authentication
export async function GET(request: NextRequest) {
  try {
    // For server-side rendering, return default projects
    // Client-side will load from localStorage
    const projects = [
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

    return NextResponse.json({
      projects,
      pagination: {
        page: 1,
        limit: 20,
        total: projects.length,
        totalPages: 1,
      }
    });
  } catch (error) {
    console.error('Error fetching demo projects:', error);
    return NextResponse.json(
      { error: 'Failed to fetch demo projects' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Create demo project
    const project = {
      id: `demo-${Date.now()}`,
      name: body.name || 'New Demo Project',
      description: body.description || 'Created in demo mode',
      industry: body.industry || '',
      brandGuidelines: body.brandGuidelines || '',
      status: 'draft' as const,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      userId: 'demo-user-123',
    };

    console.log('Demo project created:', project.name);

    return NextResponse.json({ 
      project,
      message: 'Project created successfully in demo mode'
    }, { status: 201 });
  } catch (error) {
    console.error('Demo project creation error:', error);
    return NextResponse.json(
      { error: 'Failed to create demo project' },
      { status: 500 }
    );
  }
}