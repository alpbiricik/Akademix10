export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").trim();
export const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || "").trim();
export const SUPABASE_PUBLISHABLE_KEY = (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "").trim();
