import { FileText, Grid2x2, LayoutPanelLeft, Settings } from "lucide-react";

const navItems = [
  { icon: Grid2x2, label: "Dashboard" },
  { icon: FileText, label: "Documents" },
  { icon: LayoutPanelLeft, label: "Editor" },
  { icon: Settings, label: "Settings" }
];

export function SideBar() {
  return (
    <aside className="flex h-full w-[280px] flex-col gap-6 border-r border-forge-border bg-forge-panel/80 px-5 py-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Workspace</p>
        <p className="mt-2 text-lg font-semibold text-white">Forge Studio</p>
      </div>
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => (
          <button
            key={item.label}
            className="flex items-center gap-3 rounded-xl border border-transparent bg-forge-card/40 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-forge-border hover:bg-forge-card/70"
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </nav>
      <div className="mt-auto rounded-2xl border border-forge-border bg-gradient-to-br from-forge-card/70 to-forge-panel/80 p-4 text-sm text-slate-200">
        <p className="font-semibold">Week 1 focus</p>
        <p className="mt-2 text-xs text-slate-400">
          Upload PDFs, decode structure, and prepare for collaborative editing.
        </p>
      </div>
    </aside>
  );
}
