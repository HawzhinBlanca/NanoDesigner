"use client";
import { fontsSchema } from "@/lib/canonSchemas";
import { useState, useEffect } from "react";
import { getCategorizedFonts, getFontPreviewText, getFontFamilyCSS, type FontCategory } from "@/lib/systemFonts";
import { ChevronDown, Plus, X, Type } from "lucide-react";

export function FontPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [font, setFont] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fontCategories, setFontCategories] = useState<FontCategory[]>([]);
  const [showSystemFonts, setShowSystemFonts] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    // Load system fonts on client side
    const categories = getCategorizedFonts();
    setFontCategories(categories);
  }, []);

  function add() {
    const fontToAdd = font.trim();
    if (!fontToAdd) return;

    const res = fontsSchema.safeParse([...value, fontToAdd]);
    if (!res.success) {
      setError(res.error.issues[0]?.message || "Invalid font");
      return;
    }
    setError(null);
    onChange(res.data);
    setFont("");
  }

  function addSystemFont(fontName: string) {
    const res = fontsSchema.safeParse([...value, fontName]);
    if (!res.success) {
      setError(res.error.issues[0]?.message || "Invalid font");
      return;
    }
    setError(null);
    onChange(res.data);
  }

  function removeFont(index: number) {
    onChange(value.filter((_, idx) => idx !== index));
  }

  return (
    <div className="space-y-3">
      {/* Manual font input */}
      <div className="space-y-2">
        <label className="text-sm font-medium flex items-center gap-2">
          <Type className="w-4 h-4" />
          Add Font
        </label>
        <div className="flex gap-2">
          <input 
            className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" 
            placeholder="Enter font name (e.g., Inter, SF Pro Text)" 
            value={font} 
            onChange={(e) => setFont(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && add()}
          />
          <button 
            onClick={add} 
            className="rounded bg-blue-600 text-white px-4 py-2 text-sm hover:bg-blue-700 transition-colors flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
      </div>

      {/* System fonts browser */}
      <div className="space-y-2">
        <button
          onClick={() => setShowSystemFonts(!showSystemFonts)}
          className="text-sm font-medium flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ChevronDown className={`w-4 h-4 transition-transform ${showSystemFonts ? 'rotate-180' : ''}`} />
          Browse System Fonts ({fontCategories.reduce((total, cat) => total + cat.fonts.length, 0)} available)
        </button>

        {showSystemFonts && (
          <div className="border rounded-lg p-3 bg-gray-50 max-h-64 overflow-y-auto">
            {fontCategories.map((category) => (
              <div key={category.name} className="mb-3">
                <button
                  onClick={() => setSelectedCategory(selectedCategory === category.name ? null : category.name)}
                  className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2 flex items-center gap-1 hover:text-gray-900"
                >
                  <ChevronDown className={`w-3 h-3 transition-transform ${selectedCategory === category.name ? 'rotate-180' : ''}`} />
                  {category.name} ({category.fonts.length})
                </button>
                
                {selectedCategory === category.name && (
                  <div className="grid gap-1">
                    {category.fonts.map((fontName) => (
                      <button
                        key={fontName}
                        onClick={() => addSystemFont(fontName)}
                        disabled={value.includes(fontName)}
                        className={`text-left p-2 rounded text-sm border transition-all ${
                          value.includes(fontName) 
                            ? 'bg-green-100 border-green-300 text-green-700 cursor-not-allowed' 
                            : 'bg-white border-gray-200 hover:bg-blue-50 hover:border-blue-300'
                        }`}
                        style={{ fontFamily: getFontFamilyCSS(fontName) }}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{fontName}</div>
                            <div className="text-xs text-gray-500">{getFontPreviewText(fontName)}</div>
                          </div>
                          {value.includes(fontName) && (
                            <span className="text-xs text-green-600 font-medium">Added</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
          {error}
        </div>
      )}

      {/* Selected fonts list */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Selected Fonts ({value.length})
        </label>
        {value.length === 0 ? (
          <div className="text-sm text-gray-500 italic border-2 border-dashed border-gray-300 rounded p-3 text-center">
            No fonts selected. Add fonts above to build your font palette.
          </div>
        ) : (
          <div className="space-y-2">
            {value.map((f, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-white border border-gray-200 rounded">
                <div className="flex-1">
                  <div className="text-sm font-medium">{f}</div>
                  <div 
                    className="text-sm text-gray-600 mt-1"
                    style={{ fontFamily: getFontFamilyCSS(f) }}
                  >
                    {getFontPreviewText(f)}
                  </div>
                </div>
                <button 
                  className="ml-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded p-1 transition-colors" 
                  onClick={() => removeFont(i)}
                  title={`Remove ${f}`}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

