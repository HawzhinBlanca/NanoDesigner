import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

// Types
interface TeamMember {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: 'owner' | 'designer' | 'viewer';
  status: 'online' | 'offline' | 'away';
  lastActive: Date;
  joinedAt: Date;
  permissions: {
    canEdit: boolean;
    canComment: boolean;
    canShare: boolean;
    canManageMembers: boolean;
    canExport: boolean;
    canDeleteProject: boolean;
  };
}

interface Comment {
  id: string;
  authorId: string;
  authorName: string;
  authorAvatar?: string;
  content: string;
  position?: {
    x: number;
    y: number;
    elementId?: string;
  };
  thread: CommentThread;
  createdAt: Date;
  updatedAt: Date;
  isResolved: boolean;
  reactions: {
    userId: string;
    emoji: string;
  }[];
  attachments?: {
    id: string;
    name: string;
    url: string;
    type: string;
  }[];
}

interface CommentThread {
  id: string;
  projectId: string;
  isResolved: boolean;
  participants: string[];
  comments: Comment[];
  createdAt: Date;
  updatedAt: Date;
}

interface Annotation {
  id: string;
  authorId: string;
  authorName: string;
  projectId: string;
  type: 'note' | 'highlight' | 'arrow' | 'shape';
  position: {
    x: number;
    y: number;
    width?: number;
    height?: number;
  };
  content: string;
  style: {
    color: string;
    backgroundColor?: string;
    borderColor?: string;
    fontSize?: number;
  };
  createdAt: Date;
  isVisible: boolean;
}

interface PresenceUser {
  id: string;
  name: string;
  avatar?: string;
  cursor?: {
    x: number;
    y: number;
  };
  selection?: {
    elementId: string;
    type: string;
  };
  lastSeen: Date;
}

interface ActivityItem {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  type: 'project_created' | 'project_updated' | 'member_added' | 'member_removed' | 
        'comment_added' | 'comment_resolved' | 'annotation_added' | 'file_uploaded' |
        'project_shared' | 'role_changed' | 'export_generated';
  action: string;
  details: {
    projectId?: string;
    projectName?: string;
    targetUserId?: string;
    targetUserName?: string;
    oldRole?: string;
    newRole?: string;
    commentId?: string;
    fileName?: string;
    [key: string]: any;
  };
  timestamp: Date;
}

interface ShareSettings {
  id: string;
  projectId: string;
  isPublic: boolean;
  shareLink?: string;
  linkExpiration?: Date;
  allowComments: boolean;
  allowDownload: boolean;
  requireAuth: boolean;
  password?: string;
  allowedDomains: string[];
  createdBy: string;
  createdAt: Date;
  accessCount: number;
}

interface CollaborationState {
  // Team Management
  teamMembers: TeamMember[];
  pendingInvites: {
    id: string;
    email: string;
    role: TeamMember['role'];
    invitedBy: string;
    invitedAt: Date;
    expiresAt: Date;
    status: 'pending' | 'accepted' | 'declined' | 'expired';
  }[];
  currentUser: TeamMember | null;

  // Comments & Annotations
  commentThreads: CommentThread[];
  annotations: Annotation[];
  activeThread: string | null;
  showComments: boolean;
  showAnnotations: boolean;

  // Real-time Presence
  presenceUsers: PresenceUser[];
  isConnected: boolean;

  // Activity Feed
  activities: ActivityItem[];
  activityFilter: ActivityItem['type'] | 'all';

  // Sharing
  shareSettings: ShareSettings[];
  activeShare: ShareSettings | null;

  // UI State
  loading: boolean;
  error: string | null;

  // Team Management Actions
  inviteTeamMember: (email: string, role: TeamMember['role']) => Promise<void>;
  updateMemberRole: (memberId: string, role: TeamMember['role']) => Promise<void>;
  removeMemberFromTeam: (memberId: string) => Promise<void>;
  acceptInvite: (inviteId: string) => Promise<void>;
  declineInvite: (inviteId: string) => Promise<void>;
  setCurrentUser: (user: TeamMember) => void;

  // Comments & Annotations Actions
  addComment: (threadId: string | null, content: string, position?: Comment['position']) => Promise<void>;
  updateComment: (commentId: string, content: string) => Promise<void>;
  deleteComment: (commentId: string) => Promise<void>;
  resolveThread: (threadId: string) => Promise<void>;
  unresolveThread: (threadId: string) => Promise<void>;
  addReaction: (commentId: string, emoji: string) => Promise<void>;
  removeReaction: (commentId: string, emoji: string) => Promise<void>;
  setActiveThread: (threadId: string | null) => void;
  toggleComments: () => void;
  toggleAnnotations: () => void;

  addAnnotation: (annotation: Omit<Annotation, 'id' | 'createdAt'>) => Promise<void>;
  updateAnnotation: (annotationId: string, updates: Partial<Annotation>) => Promise<void>;
  deleteAnnotation: (annotationId: string) => Promise<void>;
  toggleAnnotationVisibility: (annotationId: string) => void;

  // Real-time Presence Actions
  updatePresence: (cursor?: PresenceUser['cursor'], selection?: PresenceUser['selection']) => void;
  setConnectionStatus: (isConnected: boolean) => void;
  addPresenceUser: (user: PresenceUser) => void;
  removePresenceUser: (userId: string) => void;

  // Activity Feed Actions
  addActivity: (activity: Omit<ActivityItem, 'id' | 'timestamp'>) => void;
  setActivityFilter: (filter: ActivityItem['type'] | 'all') => void;
  clearActivities: () => void;

  // Sharing Actions
  createShareLink: (projectId: string, settings: Partial<ShareSettings>) => Promise<string>;
  updateShareSettings: (shareId: string, updates: Partial<ShareSettings>) => Promise<void>;
  revokeShareLink: (shareId: string) => Promise<void>;
  getShareSettings: (projectId: string) => ShareSettings | null;
  incrementShareAccess: (shareId: string) => void;

  // Utility Actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getRolePermissions: (role: TeamMember['role']) => TeamMember['permissions'];
  canUserPerformAction: (userId: string, action: keyof TeamMember['permissions']) => boolean;
}

const defaultPermissions: Record<TeamMember['role'], TeamMember['permissions']> = {
  owner: {
    canEdit: true,
    canComment: true,
    canShare: true,
    canManageMembers: true,
    canExport: true,
    canDeleteProject: true,
  },
  designer: {
    canEdit: true,
    canComment: true,
    canShare: true,
    canManageMembers: false,
    canExport: true,
    canDeleteProject: false,
  },
  viewer: {
    canEdit: false,
    canComment: true,
    canShare: false,
    canManageMembers: false,
    canExport: false,
    canDeleteProject: false,
  },
};

export const useCollaborationStore = create<CollaborationState>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Initial State
        teamMembers: [],
        pendingInvites: [],
        currentUser: null,
        commentThreads: [],
        annotations: [],
        activeThread: null,
        showComments: true,
        showAnnotations: true,
        presenceUsers: [],
        isConnected: false,
        activities: [],
        activityFilter: 'all',
        shareSettings: [],
        activeShare: null,
        loading: false,
        error: null,

        // Team Management Actions
        inviteTeamMember: async (email: string, role: TeamMember['role']) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));

            const invite = {
              id: Date.now().toString(),
              email,
              role,
              invitedBy: get().currentUser?.id || 'current-user',
              invitedAt: new Date(),
              expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
              status: 'pending' as const,
            };

            set((state) => {
              state.pendingInvites.push(invite);
              state.loading = false;
            });

            // Add activity
            get().addActivity({
              userId: get().currentUser?.id || 'current-user',
              userName: get().currentUser?.name || 'Unknown User',
              userAvatar: get().currentUser?.avatar,
              type: 'member_added',
              action: `invited ${email} as ${role}`,
              details: { targetUserId: email, newRole: role },
            });

          } catch (error) {
            set((state) => {
              state.error = 'Failed to send invitation';
              state.loading = false;
            });
          }
        },

        updateMemberRole: async (memberId: string, role: TeamMember['role']) => {
          const member = get().teamMembers.find(m => m.id === memberId);
          if (!member) return;

          const oldRole = member.role;

          set((state) => {
            const memberIndex = state.teamMembers.findIndex((m: any) => m.id === memberId);
            if (memberIndex >= 0) {
              state.teamMembers[memberIndex].role = role;
              state.teamMembers[memberIndex].permissions = defaultPermissions[role];
            }
          });

          // Add activity
          get().addActivity({
            userId: get().currentUser?.id || 'current-user',
            userName: get().currentUser?.name || 'Unknown User',
            userAvatar: get().currentUser?.avatar,
            type: 'role_changed',
            action: `changed ${member.name}'s role from ${oldRole} to ${role}`,
            details: { targetUserId: memberId, targetUserName: member.name, oldRole, newRole: role },
          });
        },

        removeMemberFromTeam: async (memberId: string) => {
          const member = get().teamMembers.find(m => m.id === memberId);
          if (!member) return;

          set((state) => {
            state.teamMembers = state.teamMembers.filter((m: any) => m.id !== memberId);
          });

          // Add activity
          get().addActivity({
            userId: get().currentUser?.id || 'current-user',
            userName: get().currentUser?.name || 'Unknown User',
            userAvatar: get().currentUser?.avatar,
            type: 'member_removed',
            action: `removed ${member.name} from the team`,
            details: { targetUserId: memberId, targetUserName: member.name },
          });
        },

        acceptInvite: async (inviteId: string) => {
          const invite = get().pendingInvites.find(i => i.id === inviteId);
          if (!invite) return;

          // Create new team member
          const newMember: TeamMember = {
            id: Date.now().toString(),
            email: invite.email,
            name: invite.email.split('@')[0] || 'Unknown', // Default name from email
            role: invite.role,
            status: 'online',
            lastActive: new Date(),
            joinedAt: new Date(),
            permissions: defaultPermissions[invite.role],
          };

          set((state) => {
            state.teamMembers.push(newMember);
            state.pendingInvites = state.pendingInvites.filter((i: any) => i.id !== inviteId);
          });
        },

        declineInvite: async (inviteId: string) => {
          set((state) => {
            const inviteIndex = state.pendingInvites.findIndex((i: any) => i.id === inviteId);
            if (inviteIndex >= 0) {
              state.pendingInvites[inviteIndex].status = 'declined';
            }
          });
        },

        setCurrentUser: (user: TeamMember) => {
          set((state) => {
            state.currentUser = user;
          });
        },

        // Comments & Annotations Actions
        addComment: async (threadId: string | null, content: string, position?: Comment['position']) => {
          const currentUser = get().currentUser;
          if (!currentUser) return;

          const commentId = Date.now().toString();
          const now = new Date();

          if (threadId) {
            // Add to existing thread
            const comment: Comment = {
              id: commentId,
              authorId: currentUser.id,
              authorName: currentUser.name,
              authorAvatar: currentUser.avatar,
              content,
              position,
              thread: { id: threadId } as CommentThread,
              createdAt: now,
              updatedAt: now,
              isResolved: false,
              reactions: [],
            };

            set((state) => {
              const threadIndex = state.commentThreads.findIndex((t: any) => t.id === threadId);
              if (threadIndex >= 0) {
                state.commentThreads[threadIndex].comments.push(comment);
                state.commentThreads[threadIndex].updatedAt = now;
                if (!state.commentThreads[threadIndex].participants.includes(currentUser.id)) {
                  state.commentThreads[threadIndex].participants.push(currentUser.id);
                }
              }
            });
          } else {
            // Create new thread
            const newThreadId = `thread-${Date.now()}`;
            const comment: Comment = {
              id: commentId,
              authorId: currentUser.id,
              authorName: currentUser.name,
              authorAvatar: currentUser.avatar,
              content,
              position,
              thread: { id: newThreadId } as CommentThread,
              createdAt: now,
              updatedAt: now,
              isResolved: false,
              reactions: [],
            };

            const newThread: CommentThread = {
              id: newThreadId,
              projectId: 'current-project', // This should come from context
              isResolved: false,
              participants: [currentUser.id],
              comments: [comment],
              createdAt: now,
              updatedAt: now,
            };

            set((state) => {
              state.commentThreads.push(newThread);
              state.activeThread = newThreadId;
            });
          }

          // Add activity
          get().addActivity({
            userId: currentUser.id,
            userName: currentUser.name,
            userAvatar: currentUser.avatar,
            type: 'comment_added',
            action: 'added a comment',
            details: { commentId },
          });
        },

        updateComment: async (commentId: string, content: string) => {
          set((state) => {
            for (const thread of state.commentThreads) {
              const commentIndex = thread.comments.findIndex((c: any) => c.id === commentId);
              if (commentIndex >= 0) {
                thread.comments[commentIndex].content = content;
                thread.comments[commentIndex].updatedAt = new Date();
                thread.updatedAt = new Date();
                break;
              }
            }
          });
        },

        deleteComment: async (commentId: string) => {
          set((state) => {
            for (const thread of state.commentThreads) {
              thread.comments = thread.comments.filter((c: any) => c.id !== commentId);
              if (thread.comments.length === 0) {
                state.commentThreads = state.commentThreads.filter((t: any) => t.id !== thread.id);
              }
            }
          });
        },

        resolveThread: async (threadId: string) => {
          set((state) => {
            const threadIndex = state.commentThreads.findIndex((t: any) => t.id === threadId);
            if (threadIndex >= 0) {
              state.commentThreads[threadIndex].isResolved = true;
              state.commentThreads[threadIndex].updatedAt = new Date();
            }
          });

          // Add activity
          const currentUser = get().currentUser;
          if (currentUser) {
            get().addActivity({
              userId: currentUser.id,
              userName: currentUser.name,
              userAvatar: currentUser.avatar,
              type: 'comment_resolved',
              action: 'resolved a comment thread',
              details: { threadId },
            });
          }
        },

        unresolveThread: async (threadId: string) => {
          set((state) => {
            const threadIndex = state.commentThreads.findIndex((t: any) => t.id === threadId);
            if (threadIndex >= 0) {
              state.commentThreads[threadIndex].isResolved = false;
              state.commentThreads[threadIndex].updatedAt = new Date();
            }
          });
        },

        addReaction: async (commentId: string, emoji: string) => {
          const currentUser = get().currentUser;
          if (!currentUser) return;

          set((state) => {
            for (const thread of state.commentThreads) {
              const commentIndex = thread.comments.findIndex((c: any) => c.id === commentId);
              if (commentIndex >= 0) {
                const comment = thread.comments[commentIndex];
                const existingReaction = comment.reactions.find((r: any) => r.userId === currentUser.id && r.emoji === emoji);
                if (!existingReaction) {
                  comment.reactions.push({ userId: currentUser.id, emoji });
                }
                break;
              }
            }
          });
        },

        removeReaction: async (commentId: string, emoji: string) => {
          const currentUser = get().currentUser;
          if (!currentUser) return;

          set((state) => {
            for (const thread of state.commentThreads) {
              const commentIndex = thread.comments.findIndex((c: any) => c.id === commentId);
              if (commentIndex >= 0) {
                const comment = thread.comments[commentIndex];
                comment.reactions = comment.reactions.filter((r: any) => !(r.userId === currentUser.id && r.emoji === emoji));
                break;
              }
            }
          });
        },

        setActiveThread: (threadId: string | null) => {
          set((state) => {
            state.activeThread = threadId;
          });
        },

        toggleComments: () => {
          set((state) => {
            state.showComments = !state.showComments;
          });
        },

        toggleAnnotations: () => {
          set((state) => {
            state.showAnnotations = !state.showAnnotations;
          });
        },

        // Annotation Actions
        addAnnotation: async (annotation: Omit<Annotation, 'id' | 'createdAt'>) => {
          const newAnnotation: Annotation = {
            ...annotation,
            id: Date.now().toString(),
            createdAt: new Date(),
          };

          set((state) => {
            state.annotations.push(newAnnotation);
          });

          // Add activity
          get().addActivity({
            userId: annotation.authorId,
            userName: annotation.authorName,
            type: 'annotation_added',
            action: 'added an annotation',
            details: { annotationId: newAnnotation.id },
          });
        },

        updateAnnotation: async (annotationId: string, updates: Partial<Annotation>) => {
          set((state) => {
            const annotationIndex = state.annotations.findIndex((a: any) => a.id === annotationId);
            if (annotationIndex >= 0) {
              Object.assign(state.annotations[annotationIndex], updates);
            }
          });
        },

        deleteAnnotation: async (annotationId: string) => {
          set((state) => {
            state.annotations = state.annotations.filter((a: any) => a.id !== annotationId);
          });
        },

        toggleAnnotationVisibility: (annotationId: string) => {
          set((state) => {
            const annotationIndex = state.annotations.findIndex((a: any) => a.id === annotationId);
            if (annotationIndex >= 0) {
              state.annotations[annotationIndex].isVisible = !state.annotations[annotationIndex].isVisible;
            }
          });
        },

        // Real-time Presence Actions
        updatePresence: (cursor?: PresenceUser['cursor'], selection?: PresenceUser['selection']) => {
          const currentUser = get().currentUser;
          if (!currentUser) return;

          set((state) => {
            const userIndex = state.presenceUsers.findIndex((u: any) => u.id === currentUser.id);
            if (userIndex >= 0) {
              if (cursor) state.presenceUsers[userIndex].cursor = cursor;
              if (selection) state.presenceUsers[userIndex].selection = selection;
              state.presenceUsers[userIndex].lastSeen = new Date();
            } else {
              state.presenceUsers.push({
                id: currentUser.id,
                name: currentUser.name,
                avatar: currentUser.avatar,
                cursor,
                selection,
                lastSeen: new Date(),
              });
            }
          });
        },

        setConnectionStatus: (isConnected: boolean) => {
          set((state) => {
            state.isConnected = isConnected;
          });
        },

        addPresenceUser: (user: PresenceUser) => {
          set((state) => {
            const existingIndex = state.presenceUsers.findIndex((u: any) => u.id === user.id);
            if (existingIndex >= 0) {
              state.presenceUsers[existingIndex] = user;
            } else {
              state.presenceUsers.push(user);
            }
          });
        },

        removePresenceUser: (userId: string) => {
          set((state) => {
            state.presenceUsers = state.presenceUsers.filter((u: any) => u.id !== userId);
          });
        },

        // Activity Feed Actions
        addActivity: (activity: Omit<ActivityItem, 'id' | 'timestamp'>) => {
          set((state) => {
            const newActivity: ActivityItem = {
              ...activity,
              id: Date.now().toString(),
              timestamp: new Date(),
            };
            state.activities.unshift(newActivity);
            
            // Keep only last 100 activities
            if (state.activities.length > 100) {
              state.activities = state.activities.slice(0, 100);
            }
          });
        },

        setActivityFilter: (filter: ActivityItem['type'] | 'all') => {
          set((state) => {
            state.activityFilter = filter;
          });
        },

        clearActivities: () => {
          set((state) => {
            state.activities = [];
          });
        },

        // Sharing Actions
        createShareLink: async (projectId: string, settings: Partial<ShareSettings>): Promise<string> => {
          const shareId = Date.now().toString();
          const shareLink = `${window.location.origin}/share/${shareId}`;
          
          const newShareSettings: ShareSettings = {
            id: shareId,
            projectId,
            isPublic: settings.isPublic ?? false,
            shareLink,
            linkExpiration: settings.linkExpiration,
            allowComments: settings.allowComments ?? true,
            allowDownload: settings.allowDownload ?? false,
            requireAuth: settings.requireAuth ?? false,
            password: settings.password,
            allowedDomains: settings.allowedDomains ?? [],
            createdBy: get().currentUser?.id || 'current-user',
            createdAt: new Date(),
            accessCount: 0,
          };

          set((state) => {
            state.shareSettings.push(newShareSettings);
            state.activeShare = newShareSettings;
          });

          // Add activity
          const currentUser = get().currentUser;
          if (currentUser) {
            get().addActivity({
              userId: currentUser.id,
              userName: currentUser.name,
              userAvatar: currentUser.avatar,
              type: 'project_shared',
              action: 'created a share link',
              details: { projectId, shareId },
            });
          }

          return shareLink;
        },

        updateShareSettings: async (shareId: string, updates: Partial<ShareSettings>) => {
          set((state) => {
            const shareIndex = state.shareSettings.findIndex((s: any) => s.id === shareId);
            if (shareIndex >= 0) {
              Object.assign(state.shareSettings[shareIndex], updates);
            }
          });
        },

        revokeShareLink: async (shareId: string) => {
          set((state) => {
            state.shareSettings = state.shareSettings.filter((s: any) => s.id !== shareId);
            if (state.activeShare?.id === shareId) {
              state.activeShare = null;
            }
          });
        },

        getShareSettings: (projectId: string): ShareSettings | null => {
          return get().shareSettings.find(s => s.projectId === projectId) || null;
        },

        incrementShareAccess: (shareId: string) => {
          set((state) => {
            const shareIndex = state.shareSettings.findIndex((s: any) => s.id === shareId);
            if (shareIndex >= 0) {
              state.shareSettings[shareIndex].accessCount++;
            }
          });
        },

        // Utility Actions
        setLoading: (loading: boolean) => {
          set((state) => {
            state.loading = loading;
          });
        },

        setError: (error: string | null) => {
          set((state) => {
            state.error = error;
          });
        },

        getRolePermissions: (role: TeamMember['role']): TeamMember['permissions'] => {
          return defaultPermissions[role];
        },

        canUserPerformAction: (userId: string, action: keyof TeamMember['permissions']): boolean => {
          const user = get().teamMembers.find(m => m.id === userId);
          if (!user) return false;
          return user.permissions[action];
        },
      })),
      {
        name: "collaboration-store",
        partialize: (state) => ({
          // Only persist certain parts of the state
          teamMembers: state.teamMembers,
          pendingInvites: state.pendingInvites,
          currentUser: state.currentUser,
          shareSettings: state.shareSettings,
          showComments: state.showComments,
          showAnnotations: state.showAnnotations,
          activityFilter: state.activityFilter,
        }),
      }
    )
  )
);