export type Card = {
  id: string;
  text: string;
  image: string | null;
  x: number;
  y: number;
  created_at: string;
};

export type BBox = { min_x: number; min_y: number; max_x: number; max_y: number };

export type Prompt = {
  id: number | null;
  text: string | null;
  night_of: string;
  in_window: boolean;
};

export type SupportResource = {
  region: string;
  name: string;
  detail: string;
  url: string | null;
};

export type PostResult =
  | { status: "published"; card: Card }
  | { status: "withheld"; detail: string; resources: SupportResource[] }
  | { status: "rejected"; detail: string }
  | { status: "rate_limited"; detail: string }
  | { status: "error"; detail: string };

export type ReportReason = "harmful" | "personal_info" | "spam" | "worried" | "other";

export type LiveStatus = "connecting" | "live" | "polling";
