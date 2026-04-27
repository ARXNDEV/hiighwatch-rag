export function getApiBaseUrl() {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.replace(/\/$/, "");
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host.endsWith("vercel.app")) {
      return "https://hiighwatch-rag.onrender.com";
    }
  }

  return "http://127.0.0.1:8000";
}

