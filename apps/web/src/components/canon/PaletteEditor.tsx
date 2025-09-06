"use client";
import { paletteSchema } from "@/lib/canonSchemas";
import { useState } from "react";

export function PaletteEditor({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  function addColor() {
    const col = input.trim();
    const res = paletteSchema.safeParse([...value, col]);
    if (!res.success) {
      setError(res.error.issues[0]?.message || "Invalid color");
      return;
    }
    setError(null);
    onChange(res.data);
    setInput("");
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input className="border rounded px-2 py-1" placeholder="#112233" value={input} onChange={(e)=>setInput(e.target.value)} />
        <button onClick={addColor} className="rounded bg-black text-white px-3 py-1 text-sm">Add</button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex flex-wrap gap-2">
        {value.map((c, i) => (
          <button key={i} onClick={() => onChange(value.filter((_, idx)=>idx!==i))} className="w-8 h-8 rounded border" style={{ backgroundColor: c }} title={c} />
        ))}
      </div>
    </div>
  );
}

