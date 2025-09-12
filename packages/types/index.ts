// This file is generated from api/openapi.yaml
// Do not edit directly.

export interface components {
  schemas: {
    RenderRequest: {
      project_id: string;
      prompts: {
        task: "create" | "edit" | "variations";
        instruction: string;
        references?: string[];
      };
      outputs: {
        count: number;
        format: "png" | "jpg" | "webp";
        dimensions: string;
      };
      constraints?: {
        palette_hex?: string[];
        fonts?: string[];
        logo_safe_zone_pct?: number;
      };
    };
    RenderResponse: {
      assets: {
        url: string;
        r2_key: string;
        synthid?: {
          present?: boolean;
          payload?: string;
        };
      }[];
      audit: {
        trace_id?: string;
        model_route?: string;
        cost_usd?: number;
        guardrails_ok?: boolean;
        verified_by?: "declared" | "external" | "none";
        // Manually added based on usage in composer.tsx
        brand_canon?: {
          canon_enforced?: boolean;
          violations_count?: number;
          confidence_score?: number;
        };
      };
    };
    IngestRequest: {
      project_id: string;
      assets: string[];
    };
    IngestResponse: {
      processed?: number;
      qdrant_ids?: string[];
    };
    CanonDeriveRequest: {
      project_id: string;
      evidence_ids: string[];
    };
    CanonDeriveResponse: {
      palette_hex?: string[];
      fonts?: string[];
      voice?: {
        tone?: string;
        dos?: string[];
        donts?: string[];
      };
    };
    CritiqueRequest: {
      project_id: string;
      asset_ids: string[];
    };
    CritiqueResponse: {
      score?: number;
      violations?: string[];
      repair_suggestions?: string[];
    };
  };
}

export interface paths {
  "/healthz": {
    get: {
      responses: {
        200: {
          description: string;
        };
      };
    };
  };
  "/metrics": {
    get: {
      responses: {
        200: {
          description: string;
        };
      };
    };
  };
  "/render": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["RenderRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["RenderResponse"];
          };
        };
        422: {
          description: string;
        };
      };
    };
  };
  "/ingest": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["IngestRequest"];
        };
      };
      responses: {
        200: {
          description: string;
          content: {
            "application/json": components["schemas"]["IngestResponse"];
          };
        };
      };
    };
  };
  "/canon/derive": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["CanonDeriveRequest"];
        };
      };
      responses: {
        200: {
          description: string;
          content: {
            "application/json": components["schemas"]["CanonDeriveResponse"];
          };
        };
      };
    };
  };
  "/critique": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["CritiqueRequest"];
        };
      };
      responses: {
        200: {
          description: string;
          content: {
            "application/json": components["schemas"]["CritiqueResponse"];
          };
        };
      };
    };
  };
}
