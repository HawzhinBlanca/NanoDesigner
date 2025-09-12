import { NextRequest, NextResponse } from 'next/server';

// Demo upload endpoint - simulates file upload without filesystem
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const projectId = formData.get('projectId') as string;
    
    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }
    
    if (!projectId) {
      return NextResponse.json(
        { error: 'No project ID provided' },
        { status: 400 }
      );
    }
    
    // Simulate successful upload with demo response
    const asset = {
      id: `asset-${Date.now()}`,
      projectId: projectId,
      fileName: file.name,
      storedFileName: `demo-${file.name}`,
      fileSize: file.size,
      fileType: file.type,
      url: `/uploads/demo/${file.name}`,
      uploadedAt: new Date().toISOString()
    };
    
    console.log('Demo asset uploaded:', asset.fileName, 'to project:', projectId);
    
    return NextResponse.json({
      message: 'File uploaded successfully in demo mode',
      asset,
      projectId: projectId
    }, { status: 200 });
    
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Failed to upload file' },
      { status: 500 }
    );
  }
}