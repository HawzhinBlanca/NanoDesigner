"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { 
  Settings, 
  Key, 
  Users, 
  Activity, 
  CreditCard, 
  BarChart3, 
  Shield, 
  Trash2, 
  RefreshCw,
  Plus,
  Eye,
  Search,
  Filter
} from 'lucide-react';
// import { useUser } from '@clerk/nextjs'; // Removed for demo mode

interface ApiKey {
  id: string;
  name: string;
  key: string;
  lastUsed: Date;
  usage: number;
  status: 'active' | 'revoked';
  createdAt: Date;
}

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'viewer';
  lastActive: Date;
  subscription: 'free' | 'pro' | 'enterprise';
  usage: {
    projects: number;
    storage: number;
    apiCalls: number;
  };
}

interface AuditLog {
  id: string;
  userId: string;
  userEmail: string;
  action: string;
  resource: string;
  timestamp: Date;
  details: string;
  ip: string;
}

interface RateLimit {
  id: string;
  endpoint: string;
  limit: number;
  window: number;
  enabled: boolean;
}

const AdminPanel: React.FC = () => {
  // const { user } = useUser(); // Removed for demo mode
  const [activeTab, setActiveTab] = useState<'api-keys' | 'users' | 'audit' | 'rate-limits' | 'analytics' | 'billing' | 'settings'>('api-keys');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  // Mock data - replace with actual API calls
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([
    {
      id: '1',
      name: 'Production API Key',
      key: 'sk-prod-...',
      lastUsed: new Date(),
      usage: 1250,
      status: 'active',
      createdAt: new Date('2024-01-15')
    },
    {
      id: '2',
      name: 'Development API Key',
      key: 'sk-dev-...',
      lastUsed: new Date(Date.now() - 24 * 60 * 60 * 1000),
      usage: 45,
      status: 'active',
      createdAt: new Date('2024-02-01')
    }
  ]);

  const [users, setUsers] = useState<User[]>([
    {
      id: '1',
      email: 'john@example.com',
      name: 'John Doe',
      role: 'user',
      lastActive: new Date(),
      subscription: 'pro',
      usage: {
        projects: 12,
        storage: 2.5,
        apiCalls: 1250
      }
    },
    {
      id: '2',
      email: 'jane@company.com',
      name: 'Jane Smith',
      role: 'admin',
      lastActive: new Date(Date.now() - 2 * 60 * 60 * 1000),
      subscription: 'enterprise',
      usage: {
        projects: 45,
        storage: 15.2,
        apiCalls: 5600
      }
    }
  ]);

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([
    {
      id: '1',
      userId: '1',
      userEmail: 'john@example.com',
      action: 'CREATE_PROJECT',
      resource: 'Project: Brand Guidelines',
      timestamp: new Date(),
      details: 'Created new project with template',
      ip: '192.168.1.100'
    },
    {
      id: '2',
      userId: '2',
      userEmail: 'jane@company.com',
      action: 'DELETE_API_KEY',
      resource: 'API Key: Legacy Key',
      timestamp: new Date(Date.now() - 30 * 60 * 1000),
      details: 'Revoked expired API key',
      ip: '10.0.0.5'
    }
  ]);

  const [rateLimits, setRateLimits] = useState<RateLimit[]>([
    {
      id: '1',
      endpoint: '/api/generate',
      limit: 100,
      window: 3600,
      enabled: true
    },
    {
      id: '2',
      endpoint: '/api/upload',
      limit: 50,
      window: 3600,
      enabled: true
    }
  ]);

  const handleCreateApiKey = () => {
    const newKey: ApiKey = {
      id: Date.now().toString(),
      name: `API Key ${apiKeys.length + 1}`,
      key: `sk-${Math.random().toString(36).substring(2, 15)}`,
      lastUsed: new Date(),
      usage: 0,
      status: 'active',
      createdAt: new Date()
    };
    setApiKeys([...apiKeys, newKey]);
  };

  const handleRevokeApiKey = (id: string) => {
    setApiKeys(apiKeys.map(key => 
      key.id === id ? { ...key, status: 'revoked' as const } : key
    ));
  };

  const handleRegenerateApiKey = (id: string) => {
    setApiKeys(apiKeys.map(key => 
      key.id === id ? { 
        ...key, 
        key: `sk-${Math.random().toString(36).substring(2, 15)}`,
        createdAt: new Date()
      } : key
    ));
  };

  const handleUpdateUserRole = (userId: string, newRole: 'admin' | 'user' | 'viewer') => {
    setUsers(users.map(user => 
      user.id === userId ? { ...user, role: newRole } : user
    ));
  };

  const renderApiKeysTab = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">API Key Management</h3>
          <p className="text-sm text-muted-foreground">Manage API keys for external integrations</p>
        </div>
        <Button onClick={handleCreateApiKey}>
          <Plus className="w-4 h-4 mr-2" />
          Create API Key
        </Button>
      </div>

      <div className="grid gap-4">
        {apiKeys.map(key => (
          <Card key={key.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-base">{key.name}</CardTitle>
                  <CardDescription>
                    Created {key.createdAt.toLocaleDateString()}
                  </CardDescription>
                </div>
                <Badge variant={key.status === 'active' ? 'default' : 'destructive'}>
                  {key.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm bg-muted px-2 py-1 rounded">
                    {key.key}***
                  </span>
                  <Button variant="ghost" size="sm">
                    <Eye className="w-4 h-4" />
                  </Button>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label>Last Used</Label>
                    <p>{key.lastUsed.toLocaleDateString()}</p>
                  </div>
                  <div>
                    <Label>Usage</Label>
                    <p>{key.usage.toLocaleString()} requests</p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleRegenerateApiKey(key.id)}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Regenerate
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => handleRevokeApiKey(key.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Revoke
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderUsersTab = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">User Management</h3>
          <p className="text-sm text-muted-foreground">Manage user accounts and permissions</p>
        </div>
        <div className="flex gap-2">
          <Input 
            placeholder="Search users..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-64"
          />
          <Button variant="outline">
            <Filter className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-4">
        {users.filter(user => 
          user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.email.toLowerCase().includes(searchTerm.toLowerCase())
        ).map(user => (
          <Card key={user.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-base">{user.name}</CardTitle>
                  <CardDescription>{user.email}</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Badge variant="outline">{user.role}</Badge>
                  <Badge>{user.subscription}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4 mb-4 text-sm">
                <div>
                  <Label>Projects</Label>
                  <p className="font-medium">{user.usage.projects}</p>
                </div>
                <div>
                  <Label>Storage (GB)</Label>
                  <p className="font-medium">{user.usage.storage}</p>
                </div>
                <div>
                  <Label>API Calls</Label>
                  <p className="font-medium">{user.usage.apiCalls.toLocaleString()}</p>
                </div>
                <div>
                  <Label>Last Active</Label>
                  <p className="font-medium">{user.lastActive.toLocaleDateString()}</p>
                </div>
              </div>
              
              <div className="flex gap-2">
                <select 
                  value={user.role} 
                  onChange={(e) => handleUpdateUserRole(user.id, e.target.value as any)}
                  className="px-3 py-1 border rounded text-sm"
                >
                  <option value="viewer">Viewer</option>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
                <Button variant="outline" size="sm">View Details</Button>
                <Button variant="destructive" size="sm">Suspend</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderAuditTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Audit Logs</h3>
        <p className="text-sm text-muted-foreground">View system activity and user actions</p>
      </div>

      <div className="grid gap-2">
        {auditLogs.map(log => (
          <Card key={log.id}>
            <CardContent className="pt-4">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{log.action}</Badge>
                    <span className="text-sm font-medium">{log.userEmail}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{log.resource}</p>
                  <p className="text-xs text-muted-foreground">{log.details}</p>
                </div>
                <div className="text-right text-sm text-muted-foreground">
                  <p>{log.timestamp.toLocaleString()}</p>
                  <p>IP: {log.ip}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderRateLimitsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Rate Limit Configuration</h3>
        <p className="text-sm text-muted-foreground">Configure API rate limits and throttling</p>
      </div>

      <div className="grid gap-4">
        {rateLimits.map(limit => (
          <Card key={limit.id}>
            <CardHeader>
              <CardTitle className="text-base">{limit.endpoint}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <Label>Requests per hour</Label>
                  <Input 
                    type="number" 
                    value={limit.limit} 
                    onChange={(e) => {
                      const newLimit = parseInt(e.target.value);
                      setRateLimits(rateLimits.map(rl => 
                        rl.id === limit.id ? { ...rl, limit: newLimit } : rl
                      ));
                    }}
                  />
                </div>
                <div>
                  <Label>Window (seconds)</Label>
                  <Input 
                    type="number" 
                    value={limit.window} 
                    onChange={(e) => {
                      const newWindow = parseInt(e.target.value);
                      setRateLimits(rateLimits.map(rl => 
                        rl.id === limit.id ? { ...rl, window: newWindow } : rl
                      ));
                    }}
                  />
                </div>
                <div className="flex items-end">
                  <Button 
                    variant={limit.enabled ? "default" : "outline"}
                    onClick={() => {
                      setRateLimits(rateLimits.map(rl => 
                        rl.id === limit.id ? { ...rl, enabled: !rl.enabled } : rl
                      ));
                    }}
                  >
                    {limit.enabled ? "Enabled" : "Disabled"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderAnalyticsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Usage Analytics</h3>
        <p className="text-sm text-muted-foreground">System usage and performance metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,234</div>
            <p className="text-xs text-muted-foreground">+12% from last month</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">API Calls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">45.2K</div>
            <p className="text-xs text-muted-foreground">+8% from last week</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">567</div>
            <p className="text-xs text-muted-foreground">+23% from last month</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.3TB</div>
            <p className="text-xs text-muted-foreground">78% of capacity</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Usage Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            <BarChart3 className="w-8 h-8 mr-2" />
            Analytics chart would be rendered here
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderBillingTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Billing & Subscriptions</h3>
        <p className="text-sm text-muted-foreground">Manage billing and subscription plans</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Free Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">845</div>
            <p className="text-sm text-muted-foreground">68% of total users</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pro Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">312</div>
            <p className="text-sm text-muted-foreground">25% of total users</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Enterprise</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">77</div>
            <p className="text-sm text-muted-foreground">7% of total users</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="flex justify-between items-center border-b pb-2">
                <div>
                  <p className="font-medium">Pro Plan - Monthly</p>
                  <p className="text-sm text-muted-foreground">user{i}@example.com</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">$29.00</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(Date.now() - i * 24 * 60 * 60 * 1000).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderSettingsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">System Settings</h3>
        <p className="text-sm text-muted-foreground">Configure system-wide settings and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>System Name</Label>
            <Input defaultValue="NanoDesigner Admin" />
          </div>
          <div>
            <Label>Support Email</Label>
            <Input defaultValue="support@nanodesigner.com" />
          </div>
          <div>
            <Label>Maintenance Mode</Label>
            <div className="flex items-center space-x-2">
              <input type="checkbox" id="maintenance" />
              <Label htmlFor="maintenance">Enable maintenance mode</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Password Requirements</Label>
            <div className="space-y-2 mt-2">
              <div className="flex items-center space-x-2">
                <input type="checkbox" id="pwd-length" defaultChecked />
                <Label htmlFor="pwd-length">Minimum 8 characters</Label>
              </div>
              <div className="flex items-center space-x-2">
                <input type="checkbox" id="pwd-special" defaultChecked />
                <Label htmlFor="pwd-special">Require special characters</Label>
              </div>
              <div className="flex items-center space-x-2">
                <input type="checkbox" id="pwd-numbers" defaultChecked />
                <Label htmlFor="pwd-numbers">Require numbers</Label>
              </div>
            </div>
          </div>
          <div>
            <Label>Session Timeout (minutes)</Label>
            <Input type="number" defaultValue="60" />
          </div>
        </CardContent>
      </Card>
    </div>
  );

  // Authentication check disabled for demo mode

  const tabs = [
    { id: 'api-keys' as const, label: 'API Keys', icon: Key },
    { id: 'users' as const, label: 'Users', icon: Users },
    { id: 'audit' as const, label: 'Audit Logs', icon: Activity },
    { id: 'rate-limits' as const, label: 'Rate Limits', icon: Shield },
    { id: 'analytics' as const, label: 'Analytics', icon: BarChart3 },
    { id: 'billing' as const, label: 'Billing', icon: CreditCard },
    { id: 'settings' as const, label: 'Settings', icon: Settings }
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Admin Panel</h1>
          <p className="text-muted-foreground">Manage your NanoDesigner instance</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <div className="lg:w-64 space-y-2">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? "default" : "ghost"}
                  className="w-full justify-start"
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {tab.label}
                </Button>
              );
            })}
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {activeTab === 'api-keys' && renderApiKeysTab()}
            {activeTab === 'users' && renderUsersTab()}
            {activeTab === 'audit' && renderAuditTab()}
            {activeTab === 'rate-limits' && renderRateLimitsTab()}
            {activeTab === 'analytics' && renderAnalyticsTab()}
            {activeTab === 'billing' && renderBillingTab()}
            {activeTab === 'settings' && renderSettingsTab()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;