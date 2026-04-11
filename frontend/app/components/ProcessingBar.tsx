type ProcessingBarProps = {
  active: boolean;
  progress: number;
  stageLabel: string;
};

export default function ProcessingBar({ active, progress, stageLabel }: ProcessingBarProps) {
  if (!active) {
    return null;
  }

  return (
    <section className="surface-card p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-600">Processing Application</p>
        <p className="text-sm font-semibold text-slate-900">{Math.round(progress)}%</p>
      </div>
      <p className="mt-2 text-sm text-slate-700">{stageLabel}</p>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-700 via-indigo-600 to-slate-700 transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </section>
  );
}
