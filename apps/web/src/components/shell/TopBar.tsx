"use client";

import { Bell, Search } from "lucide-react";
import { forgeTokens } from "@/lib/theme/tokens";

export function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-forge-border bg-forge-panel/80 px-6 py-4 backdrop-blur">
      <div className="flex items-center gap-4">
        <div
          className={`rounded-full bg-gradient-to-r ${forgeTokens.brand.gradient} px-4 py-1 text-sm font-semibold uppercase tracking-[0.2em] text-white shadow-glow`}
        >
          {forgeTokens.brand.name}
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-forge-border bg-forge-card/60 px-3 py-1 text-sm text-slate-300 md:flex">
          <Search className="h-4 w-4" />
          Search documents, edits, or chats
        </div>
      </div>
      <div className="flex items-center gap-3 text-slate-300">
        <button className="rounded-full border border-forge-border bg-forge-card/70 px-3 py-2 text-xs uppercase tracking-[0.2em] text-slate-200">
          Week 1
        </button>
        <button className="rounded-full border border-forge-border bg-forge-card/70 p-2">
          <Bell className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
