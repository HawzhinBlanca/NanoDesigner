"use client";
import { useRef, useState } from "react";

type V = { id: string; previewUrl?: string; finalUrl?: string };

export function CompareGrid({ variants }: { variants: V[] }) {
  const [index, setIndex] = useState(0);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const imageUrl = variants[index]?.finalUrl || variants[index]?.previewUrl || "";

  function onTouchStart(e: React.TouchEvent) {
    const t = e.touches;
    (containerRef.current as any)._touch = {
      startX: t[0]?.clientX,
      startY: t[0]?.clientY,
      startDist:
        t.length >= 2
          ? Math.hypot(t[0]!.clientX - t[1]!.clientX, t[0]!.clientY - t[1]!.clientY)
          : null,
      startScale: scale,
      startOffset: { ...offset },
    };
  }

  function onTouchMove(e: React.TouchEvent) {
    const ctx = (containerRef.current as any)._touch;
    if (!ctx) return;
    const t = e.touches;
    if (t.length >= 2 && ctx.startDist) {
      const dist = Math.hypot(t[0]!.clientX - t[1]!.clientX, t[0]!.clientY - t[1]!.clientY);
      const factor = dist / ctx.startDist;
      setScale(Math.min(3, Math.max(1, ctx.startScale * factor)));
    } else if (t.length === 1) {
      const dx = t[0]!.clientX - ctx.startX;
      const dy = t[0]!.clientY - ctx.startY;
      if (Math.abs(dx) > 50 && Math.abs(dy) < 40) {
        // swipe horizontally to switch
        if (dx < 0 && index < variants.length - 1) setIndex(index + 1);
        if (dx > 0 && index > 0) setIndex(index - 1);
        (containerRef.current as any)._touch = null;
      } else {
        setOffset({ x: ctx.startOffset.x + dx, y: ctx.startOffset.y + dy });
      }
    }
  }

  function onTouchEnd() {
    (containerRef.current as any)._touch = null;
  }

  if (!variants.length) return <div className="text-sm text-muted-foreground">Select at least two variants</div>;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <div>Variant {index + 1} / {variants.length}</div>
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 border rounded" onClick={()=> setScale(1)}>Reset</button>
          <button className="px-2 py-1 border rounded" onClick={()=> index>0 && setIndex(index-1)}>Prev</button>
          <button className="px-2 py-1 border rounded" onClick={()=> index<variants.length-1 && setIndex(index+1)}>Next</button>
        </div>
      </div>
      <div
        ref={containerRef}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        className="relative overflow-hidden rounded-lg bg-muted/20 min-h-[300px]"
        style={{ touchAction: "none" }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Compare"
            style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`, transformOrigin: "center" }}
            className="max-w-full h-auto block mx-auto select-none"
            draggable={false}
          />
        ) : (
          <div className="p-8 text-center text-sm text-muted-foreground">No image</div>
        )}
      </div>
    </div>
  );
}

