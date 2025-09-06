import posthog from "posthog-js";

export const track = {
  assetUploaded(projectId: string, count: number) {
    posthog.capture("asset_uploaded", { project_id: projectId, count });
  },
  canonSaved(projectId: string) {
    posthog.capture("canon_saved", { project_id: projectId });
  },
  previewStarted(projectId: string) {
    posthog.capture("preview_started", { project_id: projectId });
  },
  renderCompleted(projectId: string) {
    posthog.capture("render_completed", { project_id: projectId });
  },
  variantChosen(projectId: string, variantId: string) {
    posthog.capture("variant_chosen", { project_id: projectId, variant_id: variantId });
  },
  templateApplied(projectId: string, templateId: string) {
    posthog.capture("template_applied", { project_id: projectId, template_id: templateId });
  }
};

