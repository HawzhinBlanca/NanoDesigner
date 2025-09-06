"use client";

import { useEffect, useState } from "react";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { useCanonStore } from "@/stores/useCanonStore";
import { api, type CanonDeriveRequest, type CanonDeriveResponse } from "@/lib/api";
import { FileUploader } from "@/components/upload/FileUploader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { 
  Palette, 
  Type, 
  MessageSquare, 
  History, 
  Upload, 
  FileText, 
  Image,
  Save,
  Plus,
  X,
  Eye,
  Download
} from "lucide-react";

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  label: string;
}

function ColorPicker({ color, onChange, label }: ColorPickerProps) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{label}</Label>
      <div className="flex items-center gap-2">
        <div 
          className="w-8 h-8 rounded border cursor-pointer"
          style={{ backgroundColor: color }}
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'color';
            input.value = color;
            input.onchange = (e) => onChange((e.target as HTMLInputElement).value);
            input.click();
          }}
        />
        <Input
          value={color}
          onChange={(e) => onChange(e.target.value)}
          className="font-mono text-sm"
          placeholder="#000000"
        />
      </div>
    </div>
  );
}

function ColorPaletteEditor() {
  const { currentCanon, updatePalette } = useCanonStore();
  const palette = currentCanon?.palette;

  if (!palette) return null;

  const addCustomColor = () => {
    updatePalette({
      custom: [...palette.custom, "#000000"]
    });
  };

  const removeCustomColor = (index: number) => {
    const newCustom = palette.custom.filter((_, i) => i !== index);
    updatePalette({ custom: newCustom });
  };

  const updateCustomColor = (index: number, color: string) => {
    const newCustom = [...palette.custom];
    newCustom[index] = color;
    updatePalette({ custom: newCustom });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Palette className="w-4 h-4" />
          <CardTitle className="text-base">Color Palette</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <ColorPicker
            color={palette.primary}
            onChange={(color) => updatePalette({ primary: color })}
            label="Primary"
          />
          <ColorPicker
            color={palette.secondary}
            onChange={(color) => updatePalette({ secondary: color })}
            label="Secondary"
          />
          <ColorPicker
            color={palette.accent}
            onChange={(color) => updatePalette({ accent: color })}
            label="Accent"
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">Custom Colors</Label>
            <Button
              size="sm"
              variant="outline"
              onClick={addCustomColor}
            >
              <Plus className="w-3 h-3 mr-1" />
              Add
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {palette.custom.map((color, index) => (
              <div key={index} className="flex items-center gap-1">
                <div
                  className="w-6 h-6 rounded border cursor-pointer flex-shrink-0"
                  style={{ backgroundColor: color }}
                  onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'color';
                    input.value = color;
                    input.onchange = (e) => updateCustomColor(index, (e.target as HTMLInputElement).value);
                    input.click();
                  }}
                />
                <Input
                  value={color}
                  onChange={(e) => updateCustomColor(index, e.target.value)}
                  className="font-mono text-xs h-6"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeCustomColor(index)}
                  className="h-6 w-6 p-0"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="flex flex-wrap gap-2">
            {[palette.primary, palette.secondary, palette.accent, ...palette.custom].map((color, index) => (
              <div
                key={index}
                className="w-12 h-12 rounded-lg border-2 border-white shadow-sm"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function TypographyEditor() {
  const { currentCanon, updateTypography } = useCanonStore();
  const typography = currentCanon?.typography;

  if (!typography) return null;

  const fontOptions = [
    "Inter",
    "Roboto",
    "Open Sans",
    "Lato",
    "Montserrat",
    "Source Sans Pro",
    "Raleway",
    "Nunito",
    "Poppins",
    "Merriweather",
    "Playfair Display",
    "Georgia",
    "Times New Roman",
    "Arial",
    "Helvetica"
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Type className="w-4 h-4" />
          <CardTitle className="text-base">Typography</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-4">
          <div>
            <Label className="text-sm font-medium">Heading Font</Label>
            <select
              value={typography.headingFont}
              onChange={(e) => updateTypography({ headingFont: e.target.value })}
              className="w-full mt-1 px-3 py-2 border rounded-md bg-white text-sm"
            >
              {fontOptions.map((font) => (
                <option key={font} value={font}>{font}</option>
              ))}
            </select>
            <div className="mt-2 p-2 border rounded text-xl" style={{ fontFamily: typography.headingFont }}>
              Sample Heading
            </div>
          </div>

          <div>
            <Label className="text-sm font-medium">Body Font</Label>
            <select
              value={typography.bodyFont}
              onChange={(e) => updateTypography({ bodyFont: e.target.value })}
              className="w-full mt-1 px-3 py-2 border rounded-md bg-white text-sm"
            >
              {fontOptions.map((font) => (
                <option key={font} value={font}>{font}</option>
              ))}
            </select>
            <div className="mt-2 p-2 border rounded" style={{ fontFamily: typography.bodyFont }}>
              Sample body text that shows how this font looks in paragraphs.
            </div>
          </div>

          <div>
            <Label className="text-sm font-medium">Display Font (Optional)</Label>
            <select
              value={typography.displayFont || ''}
              onChange={(e) => updateTypography({ displayFont: e.target.value || undefined })}
              className="w-full mt-1 px-3 py-2 border rounded-md bg-white text-sm"
            >
              <option value="">None</option>
              {fontOptions.map((font) => (
                <option key={font} value={font}>{font}</option>
              ))}
            </select>
            {typography.displayFont && (
              <div className="mt-2 p-2 border rounded text-2xl font-bold" style={{ fontFamily: typography.displayFont }}>
                Display Text
              </div>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">Type Scale</Label>
          <div className="space-y-2">
            {Object.entries(typography.sizes).map(([key, size]) => (
              <div key={key} className="flex items-center gap-2">
                <Label className="w-12 text-xs capitalize">{key}:</Label>
                <Input
                  value={size}
                  onChange={(e) => updateTypography({
                    sizes: { ...typography.sizes, [key]: e.target.value }
                  })}
                  className="text-sm"
                  placeholder="e.g., 1.5rem"
                />
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function VoiceAndToneEditor() {
  const { currentCanon, updateVoice } = useCanonStore();
  const voice = currentCanon?.voice;
  const [newPersonality, setNewPersonality] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [newAvoidWord, setNewAvoidWord] = useState("");

  if (!voice) return null;

  const addPersonality = () => {
    if (newPersonality.trim()) {
      updateVoice({
        personality: [...voice.personality, newPersonality.trim()]
      });
      setNewPersonality("");
    }
  };

  const removePersonality = (index: number) => {
    const newPersonalities = voice.personality.filter((_, i) => i !== index);
    updateVoice({ personality: newPersonalities });
  };

  const addKeyword = () => {
    if (newKeyword.trim()) {
      updateVoice({
        keywords: [...voice.keywords, newKeyword.trim()]
      });
      setNewKeyword("");
    }
  };

  const removeKeyword = (index: number) => {
    const newKeywords = voice.keywords.filter((_, i) => i !== index);
    updateVoice({ keywords: newKeywords });
  };

  const addAvoidWord = () => {
    if (newAvoidWord.trim()) {
      updateVoice({
        avoidWords: [...voice.avoidWords, newAvoidWord.trim()]
      });
      setNewAvoidWord("");
    }
  };

  const removeAvoidWord = (index: number) => {
    const newAvoidWords = voice.avoidWords.filter((_, i) => i !== index);
    updateVoice({ avoidWords: newAvoidWords });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-4 h-4" />
          <CardTitle className="text-base">Voice & Tone</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="text-sm font-medium">Tone</Label>
          <select
            value={voice.tone}
            onChange={(e) => updateVoice({ tone: e.target.value as any })}
            className="w-full mt-1 px-3 py-2 border rounded-md bg-white text-sm"
          >
            <option value="formal">Formal</option>
            <option value="casual">Casual</option>
            <option value="playful">Playful</option>
            <option value="serious">Serious</option>
            <option value="professional">Professional</option>
          </select>
        </div>

        <div>
          <Label className="text-sm font-medium">Personality Traits</Label>
          <div className="flex gap-2 mt-1">
            <Input
              value={newPersonality}
              onChange={(e) => setNewPersonality(e.target.value)}
              placeholder="Add personality trait"
              className="text-sm"
              onKeyPress={(e) => e.key === 'Enter' && addPersonality()}
            />
            <Button size="sm" onClick={addPersonality}>
              <Plus className="w-3 h-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {voice.personality.map((trait, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {trait}
                <button
                  onClick={() => removePersonality(index)}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <Label className="text-sm font-medium">Preferred Keywords</Label>
          <div className="flex gap-2 mt-1">
            <Input
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="Add keyword"
              className="text-sm"
              onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
            />
            <Button size="sm" onClick={addKeyword}>
              <Plus className="w-3 h-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {voice.keywords.map((keyword, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {keyword}
                <button
                  onClick={() => removeKeyword(index)}
                  className="ml-1 hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <Label className="text-sm font-medium">Words to Avoid</Label>
          <div className="flex gap-2 mt-1">
            <Input
              value={newAvoidWord}
              onChange={(e) => setNewAvoidWord(e.target.value)}
              placeholder="Add word to avoid"
              className="text-sm"
              onKeyPress={(e) => e.key === 'Enter' && addAvoidWord()}
            />
            <Button size="sm" onClick={addAvoidWord}>
              <Plus className="w-3 h-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {voice.avoidWords.map((word, index) => (
              <Badge key={index} variant="destructive" className="text-xs">
                {word}
                <button
                  onClick={() => removeAvoidWord(index)}
                  className="ml-1 hover:text-red-200"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function VersionHistory() {
  const { currentCanon, history, loadHistory, revertToVersion, isLoading } = useCanonStore();

  useEffect(() => {
    if (currentCanon?.id) {
      loadHistory(currentCanon.id);
    }
  }, [currentCanon?.id, loadHistory]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <History className="w-4 h-4" />
          <CardTitle className="text-base">Version History</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <Spinner />
          </div>
        ) : (
          <div className="space-y-2">
            {currentCanon && (
              <div className="flex items-center justify-between p-2 bg-green-50 rounded border">
                <div>
                  <div className="text-sm font-medium">Version {currentCanon.version}</div>
                  <div className="text-xs text-gray-500">Current version</div>
                </div>
                <Badge variant="default">Current</Badge>
              </div>
            )}
            {history.length === 0 ? (
              <div className="text-center py-4 text-sm text-gray-500">
                No version history available
              </div>
            ) : (
              history.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-2 border rounded">
                  <div>
                    <div className="text-sm font-medium">Version {item.version}</div>
                    <div className="text-xs text-gray-500">{item.changes}</div>
                    <div className="text-xs text-gray-400">
                      {new Date(item.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => revertToVersion(item.version)}
                    disabled={isLoading}
                  >
                    Revert
                  </Button>
                </div>
              ))
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EvidenceManager({ projectId }: { projectId: string }) {
  const { evidenceItems, extracting, addEvidence, removeEvidence, extractFromEvidence } = useCanonStore();
  const [showUploader, setShowUploader] = useState(false);

  const handleUploadComplete = (files: any[]) => {
    const urls = files.map(f => f.uploadURL || f.url).filter(Boolean);
    addEvidence(urls);
    setShowUploader(false);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Upload className="w-4 h-4" />
          <CardTitle className="text-base">Evidence & Extraction</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => setShowUploader(!showUploader)}
            variant="outline"
          >
            <Plus className="w-3 h-3 mr-1" />
            Add Evidence
          </Button>
          <Button
            size="sm"
            onClick={extractFromEvidence}
            disabled={extracting || evidenceItems.length === 0}
          >
            {extracting ? (
              <Spinner className="w-3 h-3 mr-1" />
            ) : (
              <Eye className="w-3 h-3 mr-1" />
            )}
            {extracting ? "Extracting..." : "Extract Brand Elements"}
          </Button>
        </div>

        {showUploader && (
          <div className="border rounded p-2">
            <FileUploader
              projectId={projectId}
              onUploadComplete={handleUploadComplete}
              maxNumberOfFiles={5}
              allowedFileTypes={["image/*", ".pdf", "video/*"]}
            />
          </div>
        )}

        <div className="space-y-2">
          <Label className="text-sm font-medium">Uploaded Evidence ({evidenceItems.length})</Label>
          {evidenceItems.length === 0 ? (
            <div className="text-center py-4 text-sm text-gray-500 border-2 border-dashed rounded">
              No evidence uploaded yet. Add images, PDFs, or videos to extract brand elements.
            </div>
          ) : (
            <div className="space-y-1">
              {evidenceItems.map((item, index) => (
                <div key={index} className="flex items-center justify-between p-2 border rounded text-sm">
                  <div className="flex items-center gap-2">
                    <Image className="w-4 h-4" />
                    <span className="truncate">{item}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeEvidence(item)}
                    className="h-6 w-6 p-0"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function GuidelinesEditor() {
  const { currentCanon, setGuidelines } = useCanonStore();
  const guidelines = currentCanon?.guidelines || "";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4" />
          <CardTitle className="text-base">Brand Guidelines</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <Textarea
          value={guidelines}
          onChange={(e) => setGuidelines(e.target.value)}
          placeholder="Enter your brand guidelines here... You can include usage rules, do's and don'ts, brand positioning, etc."
          className="min-h-[200px] text-sm"
        />
        <div className="mt-2 text-xs text-gray-500">
          {guidelines.length} characters
        </div>
      </CardContent>
    </Card>
  );
}

function LogoManager() {
  const { currentCanon, addLogo, removeLogo } = useCanonStore();
  const logos = currentCanon?.logos || [];
  const [newLogoUrl, setNewLogoUrl] = useState("");

  const handleAddLogo = () => {
    if (newLogoUrl.trim()) {
      addLogo(newLogoUrl.trim());
      setNewLogoUrl("");
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Image className="w-4 h-4" />
          <CardTitle className="text-base">Logo Management</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            value={newLogoUrl}
            onChange={(e) => setNewLogoUrl(e.target.value)}
            placeholder="Logo URL or upload path"
            className="text-sm"
            onKeyPress={(e) => e.key === 'Enter' && handleAddLogo()}
          />
          <Button size="sm" onClick={handleAddLogo}>
            <Plus className="w-3 h-3" />
          </Button>
        </div>

        {logos.length === 0 ? (
          <div className="text-center py-4 text-sm text-gray-500 border-2 border-dashed rounded">
            No logos uploaded yet. Add logo URLs or upload logo files.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {logos.map((logo, index) => (
              <div key={index} className="relative group">
                <div className="aspect-square border-2 border-dashed rounded p-2 flex items-center justify-center bg-gray-50">
                  <img
                    src={logo}
                    alt={`Logo ${index + 1}`}
                    className="max-w-full max-h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yMCAyOEwyMCAxMk0yMCAyOEwxNCAyMk0yMCAyOEwyNiAyMiIgc3Ryb2tlPSIjOTCA5OEE2IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K";
                    }}
                  />
                </div>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => removeLogo(logo)}
                  className="absolute top-1 right-1 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </Button>
                <div className="text-xs text-gray-500 mt-1 truncate">{logo}</div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default async function CanonPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  const {
    currentCanon,
    isDirty,
    isSaving,
    error,
    save,
    load,
    setError,
    setCanon
  } = useCanonStore();

  const [derivingFromAPI, setDerivingFromAPI] = useState(false);

  // Initialize with a default canon if none exists
  useEffect(() => {
    if (!currentCanon) {
      const defaultCanon = {
        id: resolvedParams.id,
        projectId: resolvedParams.id,
        name: "Brand Canon",
        version: 1,
        palette: {
          primary: "#000000",
          secondary: "#666666",
          accent: "#0066cc",
          neutral: ["#ffffff", "#f5f5f5", "#e5e5e5"],
          custom: []
        },
        typography: {
          headingFont: "Inter",
          bodyFont: "Inter",
          sizes: {
            h1: "2.5rem",
            h2: "2rem",
            h3: "1.5rem",
            body: "1rem",
            small: "0.875rem"
          }
        },
        voice: {
          personality: ["Professional", "Approachable"],
          tone: "professional" as const,
          keywords: [],
          avoidWords: []
        },
        logos: [],
        guidelines: "",
        createdAt: new Date(),
        updatedAt: new Date()
      };
      setCanon(defaultCanon);
    }
  }, [currentCanon, resolvedParams.id, setCanon]);

  const deriveFromEvidence = async () => {
    setDerivingFromAPI(true);
    setError(null);
    try {
      const req: CanonDeriveRequest = { 
        project_id: resolvedParams.id, 
        evidence_ids: [] 
      } as CanonDeriveRequest;
      
      const data: CanonDeriveResponse = await api.canonDerive(req);
      
      // Update the current canon with derived data
      if (currentCanon && data) {
        // Merge the derived data with current canon
        // This is a placeholder - adjust based on actual API response structure
        console.log("Derived data:", data);
      }
    } catch (err) {
      setError(`Failed to derive from evidence: ${err}`);
    } finally {
      setDerivingFromAPI(false);
    }
  };

  const handleSave = async () => {
    try {
      await save();
    } catch (err) {
      setError(`Failed to save: ${err}`);
    }
  };

  if (!currentCanon) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <SignedOut>
        <p className="text-sm">Please sign in to access Canon.</p>
        <SignInButton />
      </SignedOut>
      <SignedIn>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Brand Canon</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define and manage your brand's visual identity, voice, and guidelines
          </p>
        </div>
        <div className="flex items-center gap-2">
          {error && (
            <div className="text-sm text-red-600 mr-2">
              {error}
            </div>
          )}
          <Button
            variant="outline"
            onClick={deriveFromEvidence}
            disabled={derivingFromAPI}
          >
            {derivingFromAPI ? (
              <Spinner className="w-4 h-4 mr-2" />
            ) : (
              <Eye className="w-4 h-4 mr-2" />
            )}
            {derivingFromAPI ? "Deriving..." : "Derive from Evidence"}
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isDirty || isSaving}
          >
            {isSaving ? (
              <Spinner className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {isSaving ? "Saving..." : "Save Canon"}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <div className="space-y-6">
          <ColorPaletteEditor />
          <LogoManager />
        </div>
        
        <div className="space-y-6">
          <TypographyEditor />
          <VoiceAndToneEditor />
        </div>
        
        <div className="space-y-6">
          <EvidenceManager projectId={resolvedParams.id} />
          <VersionHistory />
          <GuidelinesEditor />
        </div>
      </div>

      {/* Status */}
      {isDirty && (
        <div className="fixed bottom-4 right-4 bg-yellow-100 border border-yellow-300 rounded-lg p-3 shadow-lg">
          <div className="text-sm text-yellow-800">
            You have unsaved changes
          </div>
        </div>
      )}
      </SignedIn>
    </div>
  );
}
