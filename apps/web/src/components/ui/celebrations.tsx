"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Trophy, Star, Sparkles, PartyPopper } from "lucide-react";

interface Particle {
  id: number;
  x: number;
  y: number;
  color: string;
  delay: number;
  duration: number;
}

// Confetti component for success celebrations
export function Confetti({ 
  active = false, 
  duration = 3000 
}: { 
  active?: boolean;
  duration?: number;
}) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (!active) return;

    const colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#FFD700"];
    const newParticles: Particle[] = [];

    for (let i = 0; i < 50; i++) {
      newParticles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: Math.random() * 0.5,
        duration: 2 + Math.random() * 2,
      });
    }

    setParticles(newParticles);

    const timer = setTimeout(() => {
      setParticles([]);
    }, duration);

    return () => clearTimeout(timer);
  }, [active, duration]);

  if (!active || particles.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="absolute w-2 h-2 rounded-full"
          style={{
            left: `${particle.x}%`,
            top: -10,
            backgroundColor: particle.color,
          }}
          animate={{
            y: window.innerHeight + 20,
            x: [0, (Math.random() - 0.5) * 200, (Math.random() - 0.5) * 400],
            rotate: [0, 360, 720],
            scale: [1, 1.2, 0.8],
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            ease: "easeOut",
          }}
        />
      ))}
    </div>
  );
}

// Success modal with animation
export function SuccessModal({ 
  show, 
  message = "Success!", 
  onClose 
}: { 
  show: boolean;
  message?: string;
  onClose?: () => void;
}) {
  useEffect(() => {
    if (show && onClose) {
      const timer = setTimeout(onClose, 3000);
      return () => clearTimeout(timer);
    }
  }, [show, onClose]);

  return (
    <AnimatePresence>
      {show && (
        <>
          <Confetti active={show} />
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="fixed inset-0 flex items-center justify-center z-50"
          >
            <motion.div
              className="bg-white dark:bg-gray-900 rounded-2xl p-8 shadow-2xl glass-panel"
              animate={{
                scale: [1, 1.05, 1],
              }}
              transition={{
                duration: 0.5,
                times: [0, 0.5, 1],
              }}
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1, rotate: 360 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center"
              >
                <CheckCircle2 className="w-12 h-12 text-white" />
              </motion.div>
              <h2 className="text-2xl font-bold text-center mb-2">{message}</h2>
              <p className="text-center text-muted-foreground">Great work!</p>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Achievement notification
export function AchievementToast({ 
  achievement,
  show 
}: { 
  achievement: {
    title: string;
    description: string;
    icon: React.ReactNode;
    rarity: "common" | "rare" | "legendary";
  };
  show: boolean;
}) {
  const getRarityColor = () => {
    switch (achievement.rarity) {
      case "legendary":
        return "from-yellow-400 to-orange-500";
      case "rare":
        return "from-purple-400 to-pink-500";
      default:
        return "from-blue-400 to-green-500";
    }
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          className="fixed top-4 right-4 z-50"
        >
          <div className="glass-panel rounded-lg p-4 min-w-[300px]">
            <div className="flex items-start space-x-3">
              <motion.div
                className={`w-12 h-12 rounded-full bg-gradient-to-br ${getRarityColor()} flex items-center justify-center text-white`}
                animate={{
                  rotate: [0, 360],
                  scale: [1, 1.2, 1],
                }}
                transition={{
                  duration: 1,
                  ease: "easeInOut",
                }}
              >
                {achievement.icon}
              </motion.div>
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">{achievement.title}</h3>
                <p className="text-sm text-muted-foreground">{achievement.description}</p>
                {achievement.rarity === "legendary" && (
                  <div className="flex mt-2">
                    {[...Array(5)].map((_, i) => (
                      <motion.div
                        key={i}
                        animate={{
                          scale: [1, 1.2, 1],
                        }}
                        transition={{
                          duration: 0.5,
                          delay: i * 0.1,
                          repeat: Infinity,
                        }}
                      >
                        <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Progress celebration bar
export function ProgressCelebration({ 
  progress, 
  milestones = [25, 50, 75, 100] 
}: { 
  progress: number;
  milestones?: number[];
}) {
  const [celebrated, setCelebrated] = useState<number[]>([]);

  useEffect(() => {
    milestones.forEach((milestone) => {
      if (progress >= milestone && !celebrated.includes(milestone)) {
        setCelebrated([...celebrated, milestone]);
      }
    });
  }, [progress, milestones, celebrated]);

  return (
    <div className="relative">
      <div className="h-4 bg-secondary rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      
      {milestones.map((milestone) => (
        <div
          key={milestone}
          className="absolute top-0 h-4 flex items-center justify-center"
          style={{ left: `${milestone}%`, transform: "translateX(-50%)" }}
        >
          <AnimatePresence>
            {progress >= milestone && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute"
              >
                {milestone === 100 ? (
                  <Trophy className="w-6 h-6 text-yellow-500" />
                ) : (
                  <Sparkles className="w-5 h-5 text-purple-500" />
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
      
      {progress === 100 && <Confetti active={true} duration={2000} />}
    </div>
  );
}

// First-time action celebration
export function FirstTimeCelebration({ 
  show, 
  action 
}: { 
  show: boolean;
  action: string;
}) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed bottom-20 left-1/2 transform -translate-x-1/2 z-50"
        >
          <div className="glass-panel rounded-full px-6 py-3 flex items-center space-x-2">
            <motion.div
              animate={{
                rotate: [0, -10, 10, -10, 0],
              }}
              transition={{
                duration: 0.5,
                repeat: 3,
              }}
            >
              <PartyPopper className="w-5 h-5 text-purple-500" />
            </motion.div>
            <span className="font-medium">First {action}! Keep it up!</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Streak counter with animation
export function StreakCounter({ days }: { days: number }) {
  return (
    <div className="flex items-center space-x-2">
      <motion.div
        className="text-2xl"
        animate={{
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 1,
          repeat: Infinity,
          repeatDelay: 2,
        }}
      >
        🔥
      </motion.div>
      <div>
        <motion.div
          className="text-2xl font-bold text-orange-500"
          key={days}
          initial={{ scale: 1.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {days}
        </motion.div>
        <div className="text-xs text-muted-foreground">day streak</div>
      </div>
    </div>
  );
}