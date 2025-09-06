"use client";
import { voiceSchema } from "@/lib/canonSchemas";
import { useState } from "react";

export function VoiceEditor({ value, onChange }: { value: { tone: string; dos: string[]; donts: string[] }; onChange: (v: { tone: string; dos: string[]; donts: string[] }) => void }) {
  const [tone, setTone] = useState(value.tone || "");
  const [dos, setDos] = useState<string[]>(value.dos || []);
  const [donts, setDonts] = useState<string[]>(value.donts || []);
  const [error, setError] = useState<string | null>(null);

  function commit() {
    const res = voiceSchema.safeParse({ tone, dos, donts });
    if (!res.success) {
      setError(res.error.issues[0]?.message || "Invalid voice");
      return;
    }
    setError(null);
    onChange(res.data);
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm mb-1">Tone</label>
        <input className="border rounded px-2 py-1 w-full" value={tone} onChange={(e)=>setTone(e.target.value)} onBlur={commit} />
      </div>
      <div>
        <label className="block text-sm mb-1">Do's</label>
        <div className="flex flex-wrap gap-2">
          {dos.map((d, i) => (
            <span key={i} className="text-sm bg-gray-100 rounded px-2 py-1">
              {d}
              <button className="ml-2 text-red-600" onClick={()=>{ const next = dos.filter((_, idx)=>idx!==i); setDos(next); onChange({ tone, dos: next, donts }); }}>×</button>
            </span>
          ))}
        </div>
        <input className="border rounded px-2 py-1 w-full mt-2" placeholder="Be clear" onKeyDown={(e)=>{ if(e.key==='Enter'){ const val=(e.target as HTMLInputElement).value.trim(); if(val){ const next=[...dos,val]; setDos(next); onChange({ tone, dos: next, donts }); (e.target as HTMLInputElement).value=''; } } }} />
      </div>
      <div>
        <label className="block text-sm mb-1">Don'ts</label>
        <div className="flex flex-wrap gap-2">
          {donts.map((d, i) => (
            <span key={i} className="text-sm bg-gray-100 rounded px-2 py-1">
              {d}
              <button className="ml-2 text-red-600" onClick={()=>{ const next = donts.filter((_, idx)=>idx!==i); setDonts(next); onChange({ tone, dos, donts: next }); }}>×</button>
            </span>
          ))}
        </div>
        <input className="border rounded px-2 py-1 w-full mt-2" placeholder="Avoid jargon" onKeyDown={(e)=>{ if(e.key==='Enter'){ const val=(e.target as HTMLInputElement).value.trim(); if(val){ const next=[...donts,val]; setDonts(next); onChange({ tone, dos, donts: next }); (e.target as HTMLInputElement).value=''; } } }} />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

