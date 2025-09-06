"use client";
import { useState } from "react";
import { useTemplatesStore } from "@/stores/useTemplatesStore";
// import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs"; // Removed for demo mode
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2, FileText, Sparkles } from "lucide-react";

export default function TemplatesPage() {
  const { items, add, update, remove } = useTemplatesStore();
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const handleCreate = () => {
    if (name && prompt) {
      add({ name, prompt });
      setName("");
      setPrompt("");
      setShowCreate(false);
    }
  };

  return (
    <main className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Templates</h1>
          <p className="text-gray-600 mt-1">
            Create and manage reusable prompt templates
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Template name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Textarea
              placeholder="Template prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="min-h-[120px]"
            />
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button
                variant="outline"
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <div className="mx-auto w-24 h-24 bg-purple-50 rounded-full flex items-center justify-center mb-4">
              <FileText className="h-10 w-10 text-purple-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No templates created yet</h3>
            <p className="text-gray-600 mb-6">Create reusable prompt templates to speed up your workflow</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => setShowCreate(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Create your first template
            </Button>
          </div>
        ) : (
          items.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <Input
                    value={template.name}
                    onChange={(e) => update(template.id, { name: e.target.value })}
                    className="font-semibold border-0 p-0 h-auto bg-transparent"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(template.id)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={template.prompt}
                  onChange={(e) => update(template.id, { prompt: e.target.value })}
                  className="mb-3"
                  rows={4}
                />
                <div className="text-xs text-gray-600">
                  Created {new Date(template.createdAt).toLocaleDateString()}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </main>
  );
}