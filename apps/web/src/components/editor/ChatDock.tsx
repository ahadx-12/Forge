import { MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ChatDock() {
  return (
    <div className="flex items-center justify-between rounded-3xl border border-ink-700 bg-ink-900/80 px-6 py-4">
      <div className="flex items-center gap-3 text-sm text-frost-200/80">
        <MessageCircle className="h-4 w-4" />
        <span>AI copilots arrive in Week 2. Draft guidance & extraction here soon.</span>
      </div>
      <Button size="sm" variant="outline">
        Coming soon
      </Button>
    </div>
  );
}
