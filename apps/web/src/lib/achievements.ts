// Professional achievement and gamification system
import { useLocalStorage } from '@/hooks/use-local-storage';
import { toast } from 'sonner';
import { Trophy, Star, Zap, Target, Award, Medal } from 'lucide-react';

// Achievement definitions
export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  category: 'creation' | 'exploration' | 'mastery' | 'social' | 'special';
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  points: number;
  requirement: {
    type: 'count' | 'streak' | 'milestone' | 'secret';
    value: number;
    current?: number;
  };
  unlockedAt?: Date;
  progress?: number;
}

// All achievements
export const achievements: Achievement[] = [
  // Creation achievements
  {
    id: 'first_creation',
    title: 'Creative Pioneer',
    description: 'Created your first design',
    icon: Star,
    category: 'creation',
    rarity: 'common',
    points: 10,
    requirement: { type: 'count', value: 1 },
  },
  {
    id: 'prolific_creator',
    title: 'Prolific Creator',
    description: 'Generated 100 designs',
    icon: Trophy,
    category: 'creation',
    rarity: 'rare',
    points: 50,
    requirement: { type: 'count', value: 100 },
  },
  {
    id: 'design_master',
    title: 'Design Master',
    description: 'Generated 1000 designs',
    icon: Award,
    category: 'creation',
    rarity: 'epic',
    points: 200,
    requirement: { type: 'count', value: 1000 },
  },
  {
    id: 'speed_demon',
    title: 'Lightning Fast',
    description: 'Generated 10 designs in under a minute',
    icon: Zap,
    category: 'creation',
    rarity: 'rare',
    points: 30,
    requirement: { type: 'milestone', value: 10 },
  },
  
  // Exploration achievements
  {
    id: 'explorer',
    title: 'Explorer',
    description: 'Used all available features',
    icon: Target,
    category: 'exploration',
    rarity: 'rare',
    points: 40,
    requirement: { type: 'milestone', value: 1 },
  },
  {
    id: 'template_master',
    title: 'Template Master',
    description: 'Used 20 different templates',
    icon: Medal,
    category: 'exploration',
    rarity: 'rare',
    points: 35,
    requirement: { type: 'count', value: 20 },
  },
  
  // Mastery achievements
  {
    id: 'perfectionist',
    title: 'Pixel Perfect',
    description: 'Generated 100 variants for a single project',
    icon: Trophy,
    category: 'mastery',
    rarity: 'epic',
    points: 100,
    requirement: { type: 'count', value: 100 },
  },
  {
    id: 'consistency_king',
    title: 'Consistency King',
    description: '30-day creation streak',
    icon: Star,
    category: 'mastery',
    rarity: 'legendary',
    points: 500,
    requirement: { type: 'streak', value: 30 },
  },
  {
    id: 'night_owl',
    title: 'Night Owl',
    description: 'Created designs past midnight',
    icon: Medal,
    category: 'mastery',
    rarity: 'common',
    points: 15,
    requirement: { type: 'secret', value: 1 },
  },
  {
    id: 'early_bird',
    title: 'Early Bird',
    description: 'Created designs before 6 AM',
    icon: Medal,
    category: 'mastery',
    rarity: 'common',
    points: 15,
    requirement: { type: 'secret', value: 1 },
  },
  
  // Special achievements
  {
    id: 'beta_tester',
    title: 'Beta Tester',
    description: 'Part of the early access program',
    icon: Award,
    category: 'special',
    rarity: 'legendary',
    points: 1000,
    requirement: { type: 'secret', value: 1 },
  },
  {
    id: 'feedback_hero',
    title: 'Feedback Hero',
    description: 'Provided valuable feedback',
    icon: Star,
    category: 'special',
    rarity: 'rare',
    points: 75,
    requirement: { type: 'secret', value: 1 },
  },
];

// User statistics tracking
export interface UserStats {
  totalDesigns: number;
  totalProjects: number;
  currentStreak: number;
  longestStreak: number;
  totalPoints: number;
  level: number;
  lastActiveDate: string;
  featuresUsed: string[];
  templatesUsed: string[];
  unlockedAchievements: string[];
  achievementProgress: Record<string, number>;
}

// Level system
const POINTS_PER_LEVEL = 100;

export function calculateLevel(points: number): number {
  return Math.floor(points / POINTS_PER_LEVEL) + 1;
}

export function calculateLevelProgress(points: number): number {
  return (points % POINTS_PER_LEVEL) / POINTS_PER_LEVEL * 100;
}

export function getNextLevelPoints(points: number): number {
  const currentLevel = calculateLevel(points);
  return currentLevel * POINTS_PER_LEVEL;
}

// Achievement manager hook
export function useAchievements() {
  const [stats, setStats] = useLocalStorage<UserStats>('userStats', {
    totalDesigns: 0,
    totalProjects: 0,
    currentStreak: 0,
    longestStreak: 0,
    totalPoints: 0,
    level: 1,
    lastActiveDate: new Date().toISOString(),
    featuresUsed: [],
    templatesUsed: [],
    unlockedAchievements: [],
    achievementProgress: {},
  });

  // Track design creation
  const trackDesignCreated = () => {
    setStats(prev => {
      const newStats = {
        ...prev,
        totalDesigns: prev.totalDesigns + 1,
      };
      
      // Check achievements
      checkAchievements(newStats, 'creation');
      
      return newStats;
    });
  };

  // Track feature usage
  const trackFeatureUsed = (featureId: string) => {
    setStats(prev => {
      if (prev.featuresUsed.includes(featureId)) return prev;
      
      const newStats = {
        ...prev,
        featuresUsed: [...prev.featuresUsed, featureId],
      };
      
      checkAchievements(newStats, 'exploration');
      
      return newStats;
    });
  };

  // Track streak
  const updateStreak = () => {
    const today = new Date().toDateString();
    const lastActive = new Date(stats.lastActiveDate).toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    setStats(prev => {
      let newStreak = prev.currentStreak;
      
      if (lastActive === today) {
        // Already active today
        return prev;
      } else if (lastActive === yesterday) {
        // Continuing streak
        newStreak = prev.currentStreak + 1;
      } else {
        // Streak broken
        newStreak = 1;
      }
      
      const newStats = {
        ...prev,
        currentStreak: newStreak,
        longestStreak: Math.max(newStreak, prev.longestStreak),
        lastActiveDate: new Date().toISOString(),
      };
      
      checkAchievements(newStats, 'mastery');
      
      return newStats;
    });
  };

  // Check and unlock achievements
  const checkAchievements = (stats: UserStats, category?: string) => {
    achievements
      .filter(a => !category || a.category === category)
      .filter(a => !stats.unlockedAchievements.includes(a.id))
      .forEach(achievement => {
        let shouldUnlock = false;
        
        switch (achievement.requirement.type) {
          case 'count':
            if (achievement.id.includes('design')) {
              shouldUnlock = stats.totalDesigns >= achievement.requirement.value;
            } else if (achievement.id.includes('template')) {
              shouldUnlock = stats.templatesUsed.length >= achievement.requirement.value;
            }
            break;
            
          case 'streak':
            shouldUnlock = stats.currentStreak >= achievement.requirement.value;
            break;
            
          case 'milestone':
            if (achievement.id === 'explorer') {
              // Check if all features are used
              const requiredFeatures = ['compose', 'canon', 'history', 'templates', 'assets'];
              shouldUnlock = requiredFeatures.every(f => stats.featuresUsed.includes(f));
            }
            break;
            
          case 'secret':
            // Handle secret achievements
            const hour = new Date().getHours();
            if (achievement.id === 'night_owl') {
              shouldUnlock = hour >= 0 && hour < 6;
            } else if (achievement.id === 'early_bird') {
              shouldUnlock = hour >= 4 && hour < 6;
            }
            break;
        }
        
        if (shouldUnlock) {
          unlockAchievement(achievement);
        }
      });
  };

  // Unlock achievement
  const unlockAchievement = (achievement: Achievement) => {
    setStats(prev => ({
      ...prev,
      unlockedAchievements: [...prev.unlockedAchievements, achievement.id],
      totalPoints: prev.totalPoints + achievement.points,
      level: calculateLevel(prev.totalPoints + achievement.points),
    }));
    
    // Show celebration
    showAchievementNotification(achievement);
  };

  // Show achievement notification
  const showAchievementNotification = (achievement: Achievement) => {
    const Icon = achievement.icon;
    
    toast.custom((t) => (
      <div className="glass-panel rounded-lg p-4 min-w-[300px]">
        <div className="flex items-start space-x-3">
          <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${getRarityGradient(achievement.rarity)} flex items-center justify-center text-white`}>
            <Icon className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">Achievement Unlocked!</h3>
            <p className="text-sm font-medium">{achievement.title}</p>
            <p className="text-xs text-muted-foreground">{achievement.description}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-xs px-2 py-0.5 rounded-full ${getRarityBadgeColor(achievement.rarity)}`}>
                {achievement.rarity}
              </span>
              <span className="text-xs text-muted-foreground">
                +{achievement.points} points
              </span>
            </div>
          </div>
        </div>
      </div>
    ), {
      duration: 5000,
    });
  };

  // Get achievement progress
  const getAchievementProgress = (achievementId: string): number => {
    const achievement = achievements.find(a => a.id === achievementId);
    if (!achievement) return 0;
    
    switch (achievement.requirement.type) {
      case 'count':
        if (achievementId.includes('design')) {
          return Math.min(100, (stats.totalDesigns / achievement.requirement.value) * 100);
        }
        break;
      case 'streak':
        return Math.min(100, (stats.currentStreak / achievement.requirement.value) * 100);
    }
    
    return stats.achievementProgress[achievementId] || 0;
  };

  return {
    stats,
    achievements: achievements.map(a => ({
      ...a,
      unlocked: stats.unlockedAchievements.includes(a.id),
      progress: getAchievementProgress(a.id),
    })),
    trackDesignCreated,
    trackFeatureUsed,
    updateStreak,
    unlockAchievement,
    level: calculateLevel(stats.totalPoints),
    levelProgress: calculateLevelProgress(stats.totalPoints),
    nextLevelPoints: getNextLevelPoints(stats.totalPoints),
  };
}

// Utility functions
function getRarityGradient(rarity: string): string {
  switch (rarity) {
    case 'legendary':
      return 'from-yellow-400 to-orange-500';
    case 'epic':
      return 'from-purple-400 to-pink-500';
    case 'rare':
      return 'from-blue-400 to-cyan-500';
    default:
      return 'from-gray-400 to-gray-500';
  }
}

function getRarityBadgeColor(rarity: string): string {
  switch (rarity) {
    case 'legendary':
      return 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400';
    case 'epic':
      return 'bg-purple-500/20 text-purple-600 dark:text-purple-400';
    case 'rare':
      return 'bg-blue-500/20 text-blue-600 dark:text-blue-400';
    default:
      return 'bg-gray-500/20 text-gray-600 dark:text-gray-400';
  }
}