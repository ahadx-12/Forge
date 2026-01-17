import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-forge-bg px-6">
      <div className="max-w-3xl rounded-3xl border border-forge-border bg-gradient-to-br from-forge-panel/80 to-forge-card/80 p-10 text-center shadow-panel">
        <p className="text-xs uppercase tracking-[0.4em] text-forge-accent-soft">Forge Week 1</p>
        <h1 className="mt-4 text-4xl font-semibold text-white md:text-5xl">
          Premium PDF intelligence workspace
        </h1>
        <p className="mt-4 text-base text-slate-300">
          Upload multi-page PDFs, inspect deterministic decode output, and prepare collaborative
          edits with a cinematic dark-mode interface.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/dashboard"
            className="rounded-full bg-forge-accent px-6 py-3 text-sm font-semibold text-white shadow-glow"
          >
            Open App
          </Link>
          <div className="rounded-full border border-forge-border bg-forge-card/60 px-6 py-3 text-xs uppercase tracking-[0.2em] text-slate-300">
            Week 1 foundation
          </div>
        </div>
      </div>
    </div>
  );
}
