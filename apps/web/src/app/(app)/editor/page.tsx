import Link from "next/link";

export default function EditorLandingPage() {
  return (
    <div className="flex h-full flex-col gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Editor</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Select a document to edit</h2>
        <p className="mt-2 text-sm text-slate-400">
          Upload a PDF or choose an existing document before jumping into the editor.
        </p>
      </div>

      <Link
        href="/documents"
        className="inline-flex w-fit items-center justify-center rounded-full bg-forge-accent px-6 py-3 text-sm font-semibold text-white shadow-glow"
      >
        Go to Documents
      </Link>
    </div>
  );
}
