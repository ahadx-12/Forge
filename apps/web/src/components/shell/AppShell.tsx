import type { ReactNode } from "react";

import { SideBar } from "@/components/shell/SideBar";
import { TopBar } from "@/components/shell/TopBar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-forge-bg">
      <SideBar />
      <div className="flex flex-1 flex-col">
        <TopBar />
        <main className="flex-1 px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
