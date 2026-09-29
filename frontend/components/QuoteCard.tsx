import { Star } from "lucide-react";

/** CSS twin of the Pillow/OpenCV card, used in demo mode. */
export default function QuoteCard({ quote, author, business }: { quote: string; author: string; business: string }) {
  return (
    <div className="relative overflow-hidden rounded-2xl p-4" style={{ background: "linear-gradient(135deg,#1b1147,#5b21b6 45%,#06b6d4 80%,#f472b6)" }}>
      <div className="rounded-xl border border-white/40 bg-white/60 p-4 text-slate-900 backdrop-blur-md">
        <div className="flex gap-0.5">{[0, 1, 2, 3, 4].map((i) => <Star key={i} size={14} className="fill-amber-400 text-amber-400" />)}</div>
        <p className="mt-2 font-serif text-base font-bold leading-snug">“{quote}”</p>
        <p className="mt-3 text-xs font-bold">— {author}</p>
        <p className="text-[11px] text-slate-600">{business}</p>
      </div>
      <p className="mt-2 text-right text-[10px] text-white/80">Made with ReviewFlow AI</p>
    </div>
  );
}
