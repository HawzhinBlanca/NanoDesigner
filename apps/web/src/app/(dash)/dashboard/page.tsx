"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { connectJobWS, type JobUpdate } from "@/lib/ws";
import {
  BarChart3,
  TrendingUp,
  Clock,
  FileImage,
  DollarSign,
  Activity,
  Users,
  Settings,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import Link from "next/link";

interface DashboardStats {
  projects: {
    total: number;
    active: number;
    trend: number;
  };
  usage: {
    renders: number;
    cost: number;
    trend: number;
  };
  queue: {
    depth: number;
    processing: number;
    eta: number;
  };
  recent: {
    renders: Array<{
      id: string;
      project: string;
      status: string;
      timestamp: Date;
      cost: number;
    }>;
  };
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    projects: { total: 5, active: 3, trend: 12.5 },
    usage: { renders: 247, cost: 42.50, trend: -5.2 },
    queue: { depth: 8, processing: 2, eta: 45 },
    recent: {
      renders: [
        { id: "r1", project: "Brand Refresh", status: "completed", timestamp: new Date(), cost: 2.5 },
        { id: "r2", project: "Product Launch", status: "processing", timestamp: new Date(), cost: 3.2 },
        { id: "r3", project: "Social Campaign", status: "queued", timestamp: new Date(), cost: 1.8 },
      ],
    },
  });

  const [liveQueue, setLiveQueue] = useState<JobUpdate[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  // Simulate initial loading
  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Connect to WebSocket for live queue updates
    try {
      const ws = connectJobWS(
        "dashboard",
        (update) => {
          setLiveQueue((prev) => [update, ...prev].slice(0, 10));
        },
        () => {
          setWsConnected(false);
        }
      );
      setWsConnected(true);

      return () => {
        ws.close();
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
    }
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "processing":
        return "bg-blue-500";
      case "queued":
        return "bg-yellow-500";
      case "failed":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusBadgeVariant = (status: string): "success" | "processing" | "warning" | "destructive" | "secondary" => {
    switch (status) {
      case "completed":
        return "success";
      case "processing":
        return "processing";
      case "queued":
        return "warning";
      case "failed":
        return "destructive";
      default:
        return "secondary";
    }
  };

  return (
    <main className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome back! Here's what's happening.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/projects/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          [...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-4 rounded" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-32 mb-3" />
                <Skeleton className="h-2 w-full" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
                <FileImage className="h-4 w-4 text-gray-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.projects.active}</div>
                <div className="flex items-center text-xs text-gray-600 mt-1">
                  <span className="flex items-center">
                    {stats.projects.trend > 0 ? (
                      <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                    )}
                    {Math.abs(stats.projects.trend)}% from last month
                  </span>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span>Total: {stats.projects.total}</span>
                    <span>{Math.round((stats.projects.active / stats.projects.total) * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(stats.projects.active / stats.projects.total) * 100}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Renders</CardTitle>
                <BarChart3 className="h-4 w-4 text-gray-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.usage.renders}</div>
                <div className="flex items-center text-xs text-gray-600 mt-1">
                  <span className="flex items-center">
                    {stats.usage.trend > 0 ? (
                      <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                    )}
                    {Math.abs(stats.usage.trend)}% from last week
                  </span>
                </div>
                <div className="mt-3 flex items-end space-x-1">
                  {[40, 60, 35, 80, 55, 90, 70].map((height, i) => (
                    <div
                      key={i}
                      className="bg-green-500 rounded-sm w-2 transition-all duration-300"
                      style={{ height: `${height * 0.4}px` }}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly Cost</CardTitle>
                <DollarSign className="h-4 w-4 text-gray-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(stats.usage.cost)}</div>
                <div className="text-xs text-gray-600">
                  {formatCurrency(1.5)} today
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Queue Depth</CardTitle>
                <Activity className="h-4 w-4 text-gray-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.queue.depth}</div>
                <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                  <span>{stats.queue.processing} processing</span>
                  <span>•</span>
                  <span>~{stats.queue.eta}s ETA</span>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex space-x-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className={`h-2 w-8 rounded-full ${
                          i <= stats.queue.processing 
                            ? 'bg-orange-500 animate-pulse' 
                            : i <= stats.queue.depth 
                            ? 'bg-yellow-300' 
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="text-xs text-gray-500">
                    {stats.queue.processing}/{stats.queue.depth}
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Renders */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Renders</CardTitle>
            <CardDescription>Your latest render jobs across all projects</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.recent.renders.map((render) => (
                <div key={render.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`h-2 w-2 rounded-full ${getStatusColor(render.status)}`} />
                    <div>
                      <p className="font-medium">{render.project}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(render.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={getStatusBadgeVariant(render.status)}>
                      {render.status}
                    </Badge>
                    <span className="text-sm font-medium">{formatCurrency(render.cost)}</span>
                  </div>
                </div>
              ))}
            </div>
            <Link href="/projects/demo/history">
              <Button variant="outline" className="w-full mt-4">
                View All History
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Live Queue */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Live Queue</CardTitle>
              {wsConnected && (
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-muted-foreground">Connected</span>
                </div>
              )}
            </div>
            <CardDescription>Real-time job processing status</CardDescription>
          </CardHeader>
          <CardContent>
            {liveQueue.length === 0 ? (
              <div className="text-center py-8">
                <Activity className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">No active jobs</p>
              </div>
            ) : (
              <div className="space-y-3">
                {liveQueue.slice(0, 5).map((job, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Spinner className="h-3 w-3" />
                      <span className="text-sm font-medium">Processing Job</span>
                    </div>
                    <Badge variant={getStatusBadgeVariant(job.status || 'processing')} className="text-xs">
                      {job.status || 'processing'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks and shortcuts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link href="/projects/demo/compose">
              <Button variant="outline" className="w-full">
                <FileImage className="h-4 w-4 mr-2" />
                New Render
              </Button>
            </Link>
            <Link href="/projects/demo/assets">
              <Button variant="outline" className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Upload Assets
              </Button>
            </Link>
            <Link href="/projects/demo/canon">
              <Button variant="outline" className="w-full">
                <Settings className="h-4 w-4 mr-2" />
                Edit Canon
              </Button>
            </Link>
            <Link href="/admin">
              <Button variant="outline" className="w-full">
                <Users className="h-4 w-4 mr-2" />
                Team Settings
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

