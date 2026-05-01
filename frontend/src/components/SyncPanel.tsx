"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Cloud, Loader2, CheckCircle2, AlertCircle, LogOut } from "lucide-react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";

export function SyncPanel({ onSyncSuccess, autoSync = false }: { onSyncSuccess: (docs: {id: string, name: string, status: string}[]) => void, autoSync?: boolean }) {
  const [syncing, setSyncing] = useState(false);
  const [folderUrl, setFolderUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error" | "processing">("idle");
  const [message, setMessage] = useState("");
  const [stats, setStats] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    // Poll for storage stats to know when background processing is done
    let interval: NodeJS.Timeout;
    
    const checkStatus = async () => {
      try {
        const res = await axios.get(`${getApiBaseUrl()}/storage/stats`);
        setStats(res.data);
        if (res.data.status === "Processing in background...") {
          setStatus("processing");
          const elapsed = typeof res.data.elapsed_seconds === "number" ? `${Math.round(res.data.elapsed_seconds)}s` : "—";
          const eta = typeof res.data.eta_seconds === "number" ? `${Math.round(res.data.eta_seconds)}s` : "—";
          const stage = res.data.progress?.stage ? String(res.data.progress.stage) : "processing";
          const done = typeof res.data.progress?.files_processed === "number" ? res.data.progress.files_processed : 0;
          const total = typeof res.data.progress?.total_files === "number" ? res.data.progress.total_files : 0;
          setMessage(`Indexing in background… Stage: ${stage}. Files: ${done}/${total}. Elapsed: ${elapsed}. ETA: ${eta}.`);
        } else if (status === "processing" && res.data.status === "Ready") {
          setStatus("success");
          setMessage("Indexing complete! Documents are ready to be queried.");
        }
      } catch (err) {
        // ignore polling errors
      }
    };

    if (status === "processing" || status === "success") {
       checkStatus();
       interval = setInterval(checkStatus, 5000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [status]);

  useEffect(() => {
    if (autoSync) {
      handleSync(true); // Force sync on auto-sync (fresh login)
    }
  }, [autoSync]);

  const handleSync = async (force: boolean = false) => {
    setSyncing(true);
    setStatus("idle");
    setMessage(force ? "Force syncing from Google Drive..." : "Syncing from Google Drive...");
    try {
      const urlParams = new URLSearchParams();
      if (force) urlParams.append("force", "true");
      if (folderUrl.trim()) urlParams.append("folder_url", folderUrl.trim());
      
      const res = await axios.post(`${getApiBaseUrl()}/sync-drive?${urlParams.toString()}`);
      if (typeof res.data?.message === "string" && res.data.message.toLowerCase().includes("sync started")) {
        setStatus("processing");
      } else {
        setStatus("success");
      }
      setMessage(res.data.message || `Successfully synced ${res.data.files_processed} files.`);
      
      if (res.data.files && res.data.files.length > 0) {
        onSyncSuccess(res.data.files.map((f: any) => ({
          id: f.id,
          name: f.name,
          status: "Synced"
        })));
      }
      
      // Clean up URL to remove ?sync=true
      router.replace("/dashboard");
    } catch (err: any) {
      setStatus("error");
      const errorMsg = err.response?.data?.detail;
      setMessage(errorMsg || "An error occurred during sync. The server might have timed out because the files were too large. Please click Sync again to continue.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 relative">
      <p className="text-white/40 text-[0.75rem] leading-relaxed font-normal px-1 mb-2">
        Fetch PDFs and TXTs from your Drive. Leave blank for root, or paste a folder link below.
      </p>

      <input
        type="text"
        placeholder="https://drive.google.com/drive/folders/..."
        value={folderUrl}
        onChange={(e) => setFolderUrl(e.target.value)}
        disabled={syncing}
        className="w-full bg-[#0A0A0A]/90 backdrop-blur-xl border border-white/10 text-white placeholder-white/30 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-white/20 focus:border-white/20 transition-all text-xs"
      />

      <button
        onClick={() => handleSync(false)}
        disabled={syncing}
        className="w-full py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2.5 transition-all relative overflow-hidden disabled:opacity-70 disabled:cursor-not-allowed bg-white text-black hover:shadow-[0_0_20px_rgba(255,255,255,0.15)] group"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-black/[0.05] to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
        {syncing ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
        ) : (
          <Cloud className="w-3.5 h-3.5 text-black" />
        )}
        {syncing ? "Syncing..." : "Sync Drive"}
      </button>
      
      <button
        onClick={() => handleSync(true)}
        disabled={syncing}
        className="w-full py-2 rounded-xl font-medium text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-white/[0.03] text-white/70 border border-white/10 hover:bg-white/5 hover:text-white"
      >
        Force Sync All Files
      </button>

      <button
        onClick={async () => {
          try {
            await axios.post(`${getApiBaseUrl()}/disconnect-drive`);
            await new Promise(r => setTimeout(r, 500));
            router.push("/");
          } catch (err: any) {
            setStatus("error");
            setMessage("Failed to logout.");
          }
        }}
        disabled={syncing}
        className="w-full py-2 rounded-xl font-medium text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-transparent text-white/40 hover:text-white hover:bg-white/[0.05]"
      >
        <LogOut className="w-3.5 h-3.5" />
        Logout & Disconnect
      </button>

      {status !== "idle" && (
        <motion.div 
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-2 p-3 rounded-xl flex items-start gap-2.5 text-xs ${
            status === "success" ? "bg-white/[0.05] border border-white/10 text-white/80" : 
            status === "processing" ? "bg-blue-500/10 border border-blue-500/20 text-blue-300" :
            "bg-red-500/10 border border-red-500/20 text-red-400"
          }`}
        >
          {status === "success" ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-white/50" /> : 
           status === "processing" ? <Loader2 className="w-3.5 h-3.5 shrink-0 mt-0.5 animate-spin text-blue-400" /> :
           <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
          <span className="leading-relaxed">{message}</span>
        </motion.div>
      )}

      {stats && (
        <div className="mt-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] text-white/60 text-[11px] space-y-1">
          <div className="flex justify-between"><span>Status</span><span className="text-white/80">{stats.status || "—"}</span></div>
          <div className="flex justify-between"><span>Docs Indexed</span><span className="text-white/80">{typeof stats.docs_indexed === "number" ? stats.docs_indexed : "—"}</span></div>
          <div className="flex justify-between"><span>Total Chunks</span><span className="text-white/80">{typeof stats.total_chunks === "number" ? stats.total_chunks : "—"}</span></div>
          <div className="flex justify-between"><span>Vectors</span><span className="text-white/80">{typeof stats.vectors === "number" ? stats.vectors : "—"}</span></div>
          <div className="flex justify-between"><span>Elapsed</span><span className="text-white/80">{typeof stats.elapsed_seconds === "number" ? `${Math.round(stats.elapsed_seconds)}s` : "—"}</span></div>
          <div className="flex justify-between"><span>ETA</span><span className="text-white/80">{typeof stats.eta_seconds === "number" ? `${Math.round(stats.eta_seconds)}s` : "—"}</span></div>
        </div>
      )}
    </div>
  );
}
