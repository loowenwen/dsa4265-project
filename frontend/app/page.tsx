import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 pb-16 pt-10 md:px-10 md:pt-14">
      <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-blue-50 p-8 shadow-[0_24px_55px_-36px_rgba(15,23,42,0.4)] md:p-12">
        <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-blue-200/35 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-slate-200/45 blur-3xl" />

        <div className="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Applicant Information Processor
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-slate-900 md:text-5xl">
              Underwriting decisions, explained with evidence.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-700">
              Submit applicant records, run default-risk and anomaly scoring, and receive a grounded
              recommendation that combines rule-based policy logic with model evidence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/apply"
                className="rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                Start New Analysis
              </Link>
              <Link
                href="/result"
                className="rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
              >
                View Latest Result
              </Link>
            </div>
          </div>

          <div className="surface-card p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Workflow</p>
            <ul className="mt-4 space-y-3 text-sm text-slate-700">
              <li>1. Intake form or file upload (CSV/XLSX/JSON)</li>
              <li>2. Deterministic normalization + validation</li>
              <li>3. Default-risk + anomaly model scoring</li>
              <li>4. Rule/AI decision alignment + explanation</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-10 grid gap-4 md:grid-cols-3">
        <article className="surface-card p-6">
          <h2 className="text-lg font-semibold text-slate-900">Accept Profile</h2>
          <p className="mt-2 text-sm text-slate-700">
            Strong repayment capacity, healthy credit history, and low loan-to-income burden.
          </p>
          <p className="mt-4 text-xs uppercase tracking-[0.14em] text-emerald-700">Expected: approve</p>
        </article>

        <article className="surface-card p-6">
          <h2 className="text-lg font-semibold text-slate-900">Manual Review Profile</h2>
          <p className="mt-2 text-sm text-slate-700">
            Borderline affordability and mixed indicators that require analyst verification.
          </p>
          <p className="mt-4 text-xs uppercase tracking-[0.14em] text-blue-700">Expected: manual review</p>
        </article>

        <article className="surface-card p-6">
          <h2 className="text-lg font-semibold text-slate-900">Reject Profile</h2>
          <p className="mt-2 text-sm text-slate-700">
            Elevated default signals with extreme debt burden and unfavorable credit pattern.
          </p>
          <p className="mt-4 text-xs uppercase tracking-[0.14em] text-rose-700">Expected: reject</p>
        </article>
      </section>
    </main>
  );
}
