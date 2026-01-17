import { Sparkles, User } from "lucide-react";

import { Button } from "@/components/ui/button";

export function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-ink-700/70 bg-ink-900/80 px-6 py-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-500 to-accent-400 text-white shadow-glow">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-frost-200/70">FORGE</p>
          <p className="text-lg font-semibold text-frost-100">Document Intelligence</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm">
          Roadmap
        </Button>
        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-ink-700 bg-ink-800">
          <User className="h-4 w-4 text-frost-200" />
        </div>
      </div>
    </header>
  );
}
