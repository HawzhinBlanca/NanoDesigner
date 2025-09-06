import { useEffect, useRef, useState } from "react";

interface SwipeHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onPinch?: (scale: number) => void;
  onRotate?: (angle: number) => void;
}

export function useMobileGestures(
  elementRef: React.RefObject<HTMLElement>,
  handlers: SwipeHandlers
) {
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [isPinching, setIsPinching] = useState(false);
  const initialDistance = useRef<number>(0);
  const initialAngle = useRef<number>(0);

  const minSwipeDistance = 50;

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        setTouchEnd(null);
        setTouchStart({
          x: e.targetTouches[0]!.clientX,
          y: e.targetTouches[0]!.clientY,
        });
      } else if (e.touches.length === 2) {
        setIsPinching(true);
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        
        // Calculate initial distance for pinch
        const dx = touch2!.clientX - touch1!.clientX;
        const dy = touch2!.clientY - touch1!.clientY;
        initialDistance.current = Math.sqrt(dx * dx + dy * dy);
        
        // Calculate initial angle for rotation
        initialAngle.current = Math.atan2(dy, dx) * (180 / Math.PI);
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        setTouchEnd({
          x: e.targetTouches[0]!.clientX,
          y: e.targetTouches[0]!.clientY,
        });
      } else if (e.touches.length === 2 && isPinching) {
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        
        // Calculate current distance
        const dx = touch2!.clientX - touch1!.clientX;
        const dy = touch2!.clientY - touch1!.clientY;
        const currentDistance = Math.sqrt(dx * dx + dy * dy);
        
        // Calculate scale
        const scale = currentDistance / initialDistance.current;
        if (handlers.onPinch) {
          handlers.onPinch(scale);
        }
        
        // Calculate rotation
        const currentAngle = Math.atan2(dy, dx) * (180 / Math.PI);
        const rotation = currentAngle - initialAngle.current;
        if (handlers.onRotate) {
          handlers.onRotate(rotation);
        }
      }
    };

    const onTouchEnd = () => {
      if (!touchStart || !touchEnd) return;
      
      const distanceX = touchStart.x - touchEnd.x;
      const distanceY = touchStart.y - touchEnd.y;
      const isLeftSwipe = distanceX > minSwipeDistance;
      const isRightSwipe = distanceX < -minSwipeDistance;
      const isUpSwipe = distanceY > minSwipeDistance;
      const isDownSwipe = distanceY < -minSwipeDistance;

      if (isLeftSwipe && Math.abs(distanceX) > Math.abs(distanceY)) {
        handlers.onSwipeLeft?.();
      }
      if (isRightSwipe && Math.abs(distanceX) > Math.abs(distanceY)) {
        handlers.onSwipeRight?.();
      }
      if (isUpSwipe && Math.abs(distanceY) > Math.abs(distanceX)) {
        handlers.onSwipeUp?.();
      }
      if (isDownSwipe && Math.abs(distanceY) > Math.abs(distanceX)) {
        handlers.onSwipeDown?.();
      }
      
      setIsPinching(false);
    };

    element.addEventListener("touchstart", onTouchStart, { passive: true });
    element.addEventListener("touchmove", onTouchMove, { passive: true });
    element.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      element.removeEventListener("touchstart", onTouchStart);
      element.removeEventListener("touchmove", onTouchMove);
      element.removeEventListener("touchend", onTouchEnd);
    };
  }, [elementRef, handlers, touchStart, touchEnd, isPinching]);

  return {
    touchStart,
    touchEnd,
    isPinching,
  };
}

export function useDoubleTap(
  callback: () => void,
  threshold: number = 300
) {
  const [lastTap, setLastTap] = useState<number>(0);

  const handleTap = () => {
    const now = Date.now();
    if (now - lastTap < threshold) {
      callback();
      setLastTap(0);
    } else {
      setLastTap(now);
    }
  };

  return handleTap;
}

export function useLongPress(
  callback: () => void,
  duration: number = 500
) {
  const [isLongPress, setIsLongPress] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const start = () => {
    timerRef.current = setTimeout(() => {
      setIsLongPress(true);
      callback();
    }, duration);
  };

  const cancel = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setIsLongPress(false);
  };

  return {
    onTouchStart: start,
    onTouchEnd: cancel,
    onTouchCancel: cancel,
    isLongPress,
  };
}