const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8002";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const companyId = localStorage.getItem("company_id") || localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (companyId) {
    headers["X-Company-Id"] = companyId;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("company_id");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

// Types
export interface LoginResponse {
  access_token: string;
  token_type: string;
  companyId: string;
}

export interface Opportunity {
  noticeId: string;
  title: string;
  solicitationNumber: string;
  postedDate: string;
  responseDeadLine: string;
  type: string;
  typeOfSetAsideDescription: string;
  naicsCodes: string[];
  resourceLinks?: string[];
}

export interface OpportunitiesResponse {
  items: Opportunity[];
  total: number;
  limit: number;
  offset: number;
}

export interface RagChunk {
  id: string;
  score: number;
  text: string;
  metadata: {
    chunk_id?: string;
    noticeId?: string;
    filename?: string;
    section_name?: string;
    section_type?: string;
    requirement_flag?: boolean;
    is_critical?: boolean;
    chunk_index?: number;
    [key: string]: unknown;
  };
}

export interface DraftProposalResponse {
  opportunity: Record<string, unknown>;
  company: Record<string, unknown>;
  attachments: Record<string, unknown>;
  ragChunks: RagChunk[];
  draft: string;
}

export interface RefineDraftResponse {
  needsClarification: boolean;
  clarificationQuestion?: string;
  draft: string;
}

export interface SignupRequest {
  companyName: string;
  companyId?: string;
  capabilitiesStatement: string;
  contact?: {
    email?: string;
    fullName?: string;
  };
}

export interface SignupResponse {
  companyId: string;
  message: string;
}

// API calls
export const api = {
  login: (companyId: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ companyId }),
    }),

  signup: (profile: SignupRequest) =>
    request<SignupResponse>("/users", {
      method: "POST",
      body: JSON.stringify(profile),
    }),

  getOpportunities: (limit = 50, offset = 0) =>
    request<OpportunitiesResponse>(
      `/opportunities?limit=${limit}&offset=${offset}`
    ),

  createDraftProposal: (noticeId: string, companyId: string) =>
    request<DraftProposalResponse>("/draft-proposal", {
      method: "POST",
      body: JSON.stringify({ noticeId, companyId, includeDraft: true }),
    }),

  refineDraft: (noticeId: string, companyId: string, currentDraft: string, refinementPrompt: string) =>
    request<RefineDraftResponse>("/draft-proposal/refine", {
      method: "POST",
      body: JSON.stringify({ noticeId, companyId, currentDraft, refinementPrompt }),
    }),
};
