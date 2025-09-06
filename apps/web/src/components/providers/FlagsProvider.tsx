"use client";
import React, { createContext, useContext } from "react";

const FEATURE_FLAGS = {
  preview_mode_v2: true,
  enable_templates: true,
  enable_collaboration: true,
  enable_advanced_composer: true,
  enable_analytics: true,
  enable_admin_panel: true,
  enable_mobile_gestures: false,
  max_upload_size: 100 * 1024 * 1024,
};

const FlagsContext = createContext(FEATURE_FLAGS);

export function AppFlagsProvider({ children }: { children: React.ReactNode }) {
  return (
    <FlagsContext.Provider value={FEATURE_FLAGS}>
      {children}
    </FlagsContext.Provider>
  );
}

export function usePreviewFlag() {
  const flags = useContext(FlagsContext);
  return flags.preview_mode_v2;
}

export function useFeatureFlag(flag: keyof typeof FEATURE_FLAGS) {
  const flags = useContext(FlagsContext);
  return flags[flag];
}

