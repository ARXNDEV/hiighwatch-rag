export function getApiBaseUrl() {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.replace(/\/$/, "");
  }

  // Force Render URL globally in case Vercel's environment variables are totally missing
  // or window is undefined during SSR
  if (process.env.NODE_ENV === "production" || (typeof window !== "undefined" && window.location.hostname.includes("vercel"))) {
    return "https://hiighwatch-rag.onrender.com";
  }

  return "http://127.0.0.1:8000";
}

