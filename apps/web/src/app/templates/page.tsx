"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, Filter, Grid, List, Star, Clock, TrendingUp, Copy, Eye } from "lucide-react";

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail: string;
  uses: number;
  rating: number;
  tags: string[];
  isPremium: boolean;
}

export default function TemplatesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [view, setView] = useState<"grid" | "list">("grid");

  // Mock templates data
  const templates: Template[] = [
    {
      id: "1",
      name: "Modern Business Card",
      description: "Clean and professional business card design",
      category: "Business",
      thumbnail: "https://placeholder.com/300x200?text=Business+Card",
      uses: 1250,
      rating: 4.8,
      tags: ["business", "professional", "minimal"],
      isPremium: false
    },
    {
      id: "2",
      name: "Social Media Banner",
      description: "Eye-catching banner for social media platforms",
      category: "Social Media",
      thumbnail: "https://placeholder.com/300x200?text=Social+Banner",
      uses: 892,
      rating: 4.6,
      tags: ["social", "banner", "marketing"],
      isPremium: false
    },
    {
      id: "3",
      name: "Event Poster",
      description: "Dynamic poster template for events and concerts",
      category: "Events",
      thumbnail: "https://placeholder.com/300x200?text=Event+Poster",
      uses: 567,
      rating: 4.9,
      tags: ["event", "poster", "promotion"],
      isPremium: true
    },
    {
      id: "4",
      name: "Product Launch",
      description: "Premium template for product announcements",
      category: "Marketing",
      thumbnail: "https://placeholder.com/300x200?text=Product+Launch",
      uses: 423,
      rating: 4.7,
      tags: ["product", "launch", "announcement"],
      isPremium: true
    },
    {
      id: "5",
      name: "Newsletter Header",
      description: "Professional newsletter header design",
      category: "Email",
      thumbnail: "https://placeholder.com/300x200?text=Newsletter",
      uses: 789,
      rating: 4.5,
      tags: ["email", "newsletter", "header"],
      isPremium: false
    },
    {
      id: "6",
      name: "Logo Presentation",
      description: "Showcase your logo in style",
      category: "Branding",
      thumbnail: "https://placeholder.com/300x200?text=Logo+Display",
      uses: 1105,
      rating: 4.8,
      tags: ["logo", "branding", "presentation"],
      isPremium: false
    }
  ];

  const categories = ["all", "Business", "Social Media", "Events", "Marketing", "Email", "Branding"];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          template.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = selectedCategory === "all" || template.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Design Templates</h1>
          <p className="text-gray-600">Start with professionally designed templates and customize them to your needs</p>
        </div>

        {/* Filters and Search */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search templates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="flex gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-4 py-2 border rounded-lg"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>
                    {cat === "all" ? "All Categories" : cat}
                  </option>
                ))}
              </select>
              
              <Button
                variant={view === "grid" ? "default" : "outline"}
                size="icon"
                onClick={() => setView("grid")}
              >
                <Grid className="h-4 w-4" />
              </Button>
              <Button
                variant={view === "list" ? "default" : "outline"}
                size="icon"
                onClick={() => setView("list")}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Templates</p>
                  <p className="text-2xl font-bold">{templates.length}</p>
                </div>
                <Grid className="h-8 w-8 text-blue-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Most Popular</p>
                  <p className="text-2xl font-bold">Business Card</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Premium Templates</p>
                  <p className="text-2xl font-bold">2</p>
                </div>
                <Star className="h-8 w-8 text-yellow-500 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Templates Grid/List */}
        <div className={view === "grid" ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" : "space-y-4"}>
          {filteredTemplates.map(template => (
            <Card key={template.id} className="overflow-hidden hover:shadow-lg transition-shadow">
              {view === "grid" ? (
                <>
                  <div className="aspect-video bg-gray-100">
                    <img
                      src={template.thumbnail}
                      alt={template.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-lg">{template.name}</h3>
                      {template.isPremium && (
                        <Badge variant="secondary" className="ml-2">
                          <Star className="h-3 w-3 mr-1" />
                          Premium
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                    
                    <div className="flex flex-wrap gap-1 mb-3">
                      {template.tags.map(tag => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    
                    <div className="flex items-center justify-between text-sm text-gray-500 mb-3">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {template.uses} uses
                      </span>
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                        {template.rating}
                      </span>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button className="flex-1" size="sm">
                        <Copy className="h-4 w-4 mr-2" />
                        Use Template
                      </Button>
                      <Button variant="outline" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </>
              ) : (
                <CardContent className="p-4">
                  <div className="flex gap-4">
                    <div className="w-32 h-24 bg-gray-100 rounded">
                      <img
                        src={template.thumbnail}
                        alt={template.name}
                        className="w-full h-full object-cover rounded"
                      />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-lg">{template.name}</h3>
                        {template.isPremium && (
                          <Badge variant="secondary">
                            <Star className="h-3 w-3 mr-1" />
                            Premium
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{template.description}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>{template.category}</span>
                        <span>{template.uses} uses</span>
                        <span className="flex items-center gap-1">
                          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          {template.rating}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      <Button size="sm">
                        Use Template
                      </Button>
                      <Button variant="outline" size="sm">
                        Preview
                      </Button>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>

        {filteredTemplates.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No templates found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}