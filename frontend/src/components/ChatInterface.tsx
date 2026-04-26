"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Sparkles, FileText, Loader2, ArrowRight } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from "axios";

interface Message {
  role: "user" | "ai";
  content: string;
  sources?: { doc_id: string; name: string; chunk_text: string }[];
}

export function ChatInterface() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load chat history on mount
    const fetchHistory = async () => {
      try {
        const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/chat/history`);
        if (res.data && res.data.history) {
          setMessages(res.data.history);
        }
      } catch (err) {
        console.error("Failed to load chat history", err);
      }
    };
    fetchHistory();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userQuery = query.trim();
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", content: userQuery }]);
    setLoading(true);

    try {
      const res = await axios.post(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/ask`, { query: userQuery });
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: res.data.answer,
          sources: res.data.sources,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Sorry, I encountered an error answering that." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full relative">
      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar"
      >
        <div className="max-w-4xl mx-auto space-y-8 pb-10">
          {messages.length === 0 ? (
            <div className="h-[60vh] flex flex-col items-center justify-center text-white/30 space-y-5 opacity-70">
              <Bot className="w-12 h-12 opacity-50" />
              <div className="text-center">
                <p className="text-xl font-medium text-white/70 mb-2">How can I help you today?</p>
                <p className="text-sm font-normal max-w-sm text-white/40">
                  Ask anything about the documents in your synced Google Drive.
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-5 w-full"
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === "user" ? "bg-white/[0.05] text-white/70 border border-white/[0.05]" : "bg-white text-black shadow-[0_0_15px_rgba(255,255,255,0.2)]"
              }`}>
                {msg.role === "user" ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
              </div>
              
              <div className="flex flex-col gap-2 min-w-0 w-full pt-1">
                <div className={`text-[0.95rem] leading-relaxed prose prose-sm prose-invert max-w-none ${
                  msg.role === "user" 
                    ? "text-white/90 font-medium prose-p:text-white/90" 
                    : "text-white/80 prose-p:text-white/80 prose-headings:text-white/90 prose-strong:text-white"
                }`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {msg.sources.map((src, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] text-white/50 hover:text-white/90 hover:bg-white/[0.08] transition-colors cursor-pointer group/src backdrop-blur-sm">
                        <FileText className="w-3 h-3" />
                        <span className="truncate max-w-[200px] font-medium">{src.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))
          )}
          
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-5"
            >
              <div className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="px-5 py-4 rounded-2xl bg-white/[0.03] border border-white/[0.05] rounded-tl-sm flex items-center gap-3 backdrop-blur-md">
                <Loader2 className="w-4 h-4 animate-spin text-white/50" />
                <span className="text-sm text-white/50 font-medium">Analyzing documents...</span>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-6 pt-0 pb-8 relative z-10 bg-gradient-to-t from-[#030303] via-[#030303]/80 to-transparent">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative flex items-center shadow-[0_0_40px_rgba(0,0,0,0.8)] rounded-2xl">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about your documents..."
              className="w-full bg-[#0A0A0A]/90 backdrop-blur-xl border border-white/10 text-white placeholder-white/30 rounded-2xl pl-6 pr-16 py-4 focus:outline-none focus:ring-1 focus:ring-white/20 focus:border-white/20 transition-all text-[0.95rem]"
            />
            <button
              type="submit"
              disabled={!query.trim() || loading}
              className="absolute right-2.5 w-10 h-10 rounded-xl bg-white text-black flex items-center justify-center hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 transition-all shadow-[0_0_15px_rgba(255,255,255,0.15)]"
            >
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
          <p className="text-center text-[10px] text-white/30 mt-3 font-medium">
            LLaMA 3.3 can make mistakes. Always verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}
