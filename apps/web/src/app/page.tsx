import Link from "next/link";
import { ArrowUpRight, Sparkles } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-ink-900">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-ink-700 bg-ink-800/60 px-4 py-2 text-xs uppercase tracking-[0.3em] text-frost-200/70">
          <Sparkles className="h-4 w-4 text-accent-400" />
          Week 1 Foundation
        </div>
        <h1 className="mt-6 text-5xl font-semibold leading-tight text-frost-100 md:text-6xl">
          Forge premium PDF workflows with deterministic intelligence.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-frost-200/80">
          Build projects, upload multi-page PDFs, and edit with a production-ready viewer.
          Extraction pipelines are already deterministic for reliable selections.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link href="/dashboard" className={buttonVariants({ size: "lg" })}>
            Open App <ArrowUpRight className="h-4 w-4" />
          </Link>
          <Button variant="outline" size="lg">
            View docs
          </Button>
        </div>
      </div>
    </div>
  );
}
