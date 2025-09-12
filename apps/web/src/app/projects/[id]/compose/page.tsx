import Composer from './composer';
import DemoComposer from './demo-composer';

export default async function ComposePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  // Always use the real composer for full production mode
  return <Composer projectId={id} />;
}