import * as React from "react";

import { cn } from "@/lib/utils";

const Badge = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full border border-ink-700 bg-ink-900/60 px-3 py-1 text-xs font-medium text-frost-100",
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = "Badge";

export { Badge };
