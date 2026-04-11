import { ReactNode } from "react";

type CollapsibleSectionProps = {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
};

export default function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: CollapsibleSectionProps) {
  return (
    <details className="surface-card group overflow-hidden" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-6 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
        </div>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600 transition group-open:rotate-180">
          v
        </span>
      </summary>
      <div className="border-t border-slate-200 px-6 py-5">{children}</div>
    </details>
  );
}
