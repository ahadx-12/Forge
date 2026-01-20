export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Settings</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Workspace preferences</h2>
        <p className="mt-2 text-sm text-slate-400">
          Settings management is coming soon. In the meantime, configure environment flags via the
          deployment settings.
        </p>
      </div>
    </div>
  );
}
