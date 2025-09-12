/**
 * Extended API types with proper typing for audit responses
 */

import type { RenderResponse } from '@/lib/api';

export interface BrandCanonInfo {
  canon_enforced: boolean;
  violations_count: number;
  confidence_score: number;
  violations?: string[];
}

export interface ExtendedAudit {
  cost_usd: number;
  trace_id: string;
  model_route: string;
  verified_by: string;
  brand_canon?: BrandCanonInfo;
  synthid_verification?: {
    detected: boolean;
    confidence: number;
  };
}

export interface ExtendedRenderResponse extends Omit<RenderResponse, 'audit'> {
  audit: ExtendedAudit;
}