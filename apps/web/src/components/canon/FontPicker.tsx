"use client";
import { fontsSchema } from "@/lib/canonSchemas";
import { useState } from "react";

export function FontPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [font, setFont] = useState("");
  const [error, setError] = useState<string | null>(null);

  function add() {
    const res = fontsSchema.safeParse([...value, font.trim()]);
    if (!res.success) {
      setError(res.error.issues[0]?.message || "Invalid font");
      return;
    }
    setError(null);
    onChange(res.data);
    setFont("");
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input className="border rounded px-2 py-1" placeholder="Inter" value={font} onChange={(e)=>setFont(e.target.value)} />
        <button onClick={add} className="rounded bg-black text-white px-3 py-1 text-sm">Add</button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex flex-wrap gap-2">
        {value.map((f, i) => (
          <span key={i} className="text-sm bg-gray-100 rounded px-2 py-1">
            {f}
            <button className="ml-2 text-red-600" onClick={()=>onChange(value.filter((_, idx)=>idx!==i))}>×</button>
          </span>
        ))}
      </div>
    </div>
  );
}

