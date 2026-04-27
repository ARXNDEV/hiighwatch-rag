export function getApiBaseUrl() {
  // 1. ALWAYS force Render URL in production (Vercel) regardless of env vars
  if (process.env.NODE_ENV === "production") {
    return "https://hiighwatch-rag-3cdc.onrender.com";
  }
  
  if (typeof window !== "undefined" && window.location.hostname.includes("vercel")) {
    return "https://hiighwatch-rag-3cdc.onrender.com";
  }

  // 2. Fallback to local dev server ONLY if we are truly running locally
  return "http://127.0.0.1:8000";
}

