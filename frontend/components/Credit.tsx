import { Github, Linkedin } from "lucide-react";
import { CREDIT } from "@/lib/config";

export default function Credit({ className = "" }: { className?: string }) {
  return (
    <footer className={`flex flex-col items-center gap-2 py-8 text-xs text-slate-400 ${className}`}>
      <p>
        Designed &amp; developed by <span className="neon-text font-bold tracking-wide">{CREDIT.name}</span>
      </p>
      <div className="flex items-center gap-4">
        <a href={CREDIT.github} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-white"><Github size={14} /> GitHub</a>
        <a href={CREDIT.linkedin} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-white"><Linkedin size={14} /> LinkedIn</a>
      </div>
      <p className="opacity-60">© {new Date().getFullYear()} ReviewFlow AI · Agentic AI · RAG · CNN Vision · Docker</p>
    </footer>
  );
}
