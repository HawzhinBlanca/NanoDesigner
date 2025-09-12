import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const { prompt, projectId = 'default' } = await request.json();
    
    if (!prompt) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }
    
    // Call the real backend /render endpoint
    const response = await fetch(`${API_BASE_URL}/render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add auth header if available
        ...(request.headers.get('authorization') && {
          'Authorization': request.headers.get('authorization') as string
        })
      },
      body: JSON.stringify({
        project_id: projectId,
        prompts: {
          instruction: prompt,
          references: []
        },
        outputs: {
          count: 1,
          format: 'png',
          dimensions: '1024x1024'
        }
      })
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.message || 'Failed to generate image' },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    // Extract the first generated image
    const image = data.images?.[0];
    if (!image) {
      return NextResponse.json(
        { error: 'No image generated' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      imageUrl: image.url,
      prompt: prompt,
      timestamp: new Date().toISOString(),
      metadata: {
        width: 1024,
        height: 1024,
        model: data.model || data.metadata?.model_used || 'production-image-server',
        cost_usd: data.cost_info?.total_cost_usd || data.cost || 0,
        trace_id: data.render_id,
        processing_time: data.processing_time_ms,
        format: image.format,
        dimensions: image.dimensions
      }
    }, { status: 200 });
    
  } catch (error) {
    console.error('Image generation error:', error);
    return NextResponse.json(
      { error: 'Failed to generate image' },
      { status: 500 }
    );
  }
}