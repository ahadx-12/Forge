import type { ReactNode } from "react";

import { SideBar } from "@/components/shell/SideBar";
import { TopBar } from "@/components/shell/TopBar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-ink-900 text-frost-100">
      <TopBar />
      <div className="flex flex-1">
        <SideBar />
        <main className="flex-1 overflow-hidden bg-gradient-to-br from-ink-900 via-ink-800 to-ink-900 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
