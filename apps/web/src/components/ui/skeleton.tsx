import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'circular' | 'rectangular'
  animation?: 'pulse' | 'wave' | 'none'
}

function Skeleton({
  className,
  variant = 'default',
  animation = 'pulse',
  ...props
}: SkeletonProps) {
  const animationClass = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer',
    none: ''
  }[animation]

  const variantClass = {
    default: 'rounded-md',
    circular: 'rounded-full',
    rectangular: 'rounded-none'
  }[variant]

  return (
    <div
      className={cn(
        "bg-gray-200 dark:bg-gray-700",
        animationClass,
        variantClass,
        className
      )}
      {...props}
    />
  )
}

// Specific skeleton components for common UI patterns
function SkeletonCard() {
  return (
    <div className="flex flex-col space-y-3">
      <Skeleton className="h-[125px] w-full rounded-xl" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-[250px]" />
        <Skeleton className="h-4 w-[200px]" />
      </div>
    </div>
  )
}

function SkeletonImage() {
  return (
    <div className="relative overflow-hidden rounded-lg">
      <Skeleton className="aspect-square w-full" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
    </div>
  )
}

function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton 
          key={i} 
          className="h-4" 
          style={{ width: `${100 - (i * 10)}%` }}
        />
      ))}
    </div>
  )
}

function SkeletonButton() {
  return <Skeleton className="h-10 w-28 rounded-md" />
}

export { 
  Skeleton, 
  SkeletonCard, 
  SkeletonImage, 
  SkeletonText, 
  SkeletonButton
}