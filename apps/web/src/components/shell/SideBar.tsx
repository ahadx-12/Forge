import Link from "next/link";
import { BookOpen, LayoutGrid, Settings } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { href: "/editor/demo", label: "Editor", icon: BookOpen },
];

export function SideBar() {
  return (
    <aside className="flex h-full w-64 flex-col justify-between border-r border-ink-700/70 bg-ink-900/70 px-4 py-6">
      <div className="space-y-6">
        <div className="rounded-3xl bg-gradient-to-br from-ink-800 to-ink-900 px-4 py-5 text-sm text-frost-200/80">
          <p className="font-semibold text-frost-100">Workspace</p>
          <p className="mt-1 text-xs uppercase tracking-[0.3em] text-frost-200/60">Week 1</p>
        </div>
        <nav className="space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-3 py-2 text-sm font-medium text-frost-200/80 transition hover:bg-ink-800 hover:text-frost-100"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3 rounded-2xl border border-ink-700 bg-ink-800/80 px-3 py-3 text-xs text-frost-200/70">
        <Settings className="h-4 w-4" />
        <span>Settings</span>
      </div>
    </aside>
  );
}
