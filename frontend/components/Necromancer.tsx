"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  exhume, getSample, listSamples, resurrect, seance,
  type Exhumed, type Sample, type SampleSummary, type SeanceResult, type Spirit,
} from "@/lib/api";

type ParagraphRange = { name: string; start: number; end: number };

/** Find where each procedure paragraph starts and ends, so we can highlight it. */
function paragraphRanges(cobol: string): ParagraphRange[] {
  const lines = cobol.split("\n");
  const procIdx = lines.findIndex((l) => /PROCEDURE DIVISION/.test(l));
  if (procIdx < 0) return [];
  const starts: { name: string; line: number }[] = [];
  for (let i = procIdx + 1; i < lines.length; i++) {
    const m = lines[i].match(/^ {7}([A-Z0-9-]+)\.\s*$/);
    if (m) starts.push({ name: m[1], line: i });
  }
  return starts.map((s, i) => ({
    name: s.name,
    start: s.line,
    end: (starts[i + 1]?.line ?? lines.length) - 1,
  }));
}

/** Swap truncation for ordinary rounding, the classic mistake in a COBOL port. */
function introduceBug(py: string): string {
  return py
    .replace(/from decimal import ([^\n]*)/, (_m, names) =>
      names.includes("ROUND_HALF_UP") ? `from decimal import ${names}` : `from decimal import ROUND_HALF_UP, ${names}`)
    .replace(/rounding=ROUND_DOWN/g, "rounding=ROUND_HALF_UP");
}

function StepHeader({ n, title, line }: { n: string; title: string; line: string }) {
  return (
    <header className="mb-10">
      <p className="font-mono text-sm tracking-wide text-muted">{n} / 03</p>
      <h2 className="headline mt-3 text-6xl sm:text-7xl">{title}</h2>
      <p className="mt-5 max-w-xl text-lg text-muted">{line}</p>
    </header>
  );
}

function ActionButton(props: { onClick: () => void; disabled?: boolean; children: React.ReactNode; quiet?: boolean }) {
  return (
    <button
      onClick={props.onClick}
      disabled={props.disabled}
      className={
        props.quiet
          ? "rounded-full border border-line px-5 py-2.5 text-sm font-medium transition-colors duration-500 hover:border-ink disabled:opacity-40"
          : "rounded-full bg-ink px-6 py-3 text-sm font-medium text-paper transition-colors duration-500 hover:bg-black disabled:opacity-40"
      }
    >
      {props.children}
    </button>
  );
}

function GreenScreen({ cobol, active }: { cobol: string; active: ParagraphRange | null }) {
  const lines = cobol.split("\n");
  const box = useRef<HTMLPreElement>(null);
  useEffect(() => {
    // Scroll inside the panel only, never the page.
    if (!active || !box.current) return;
    const row = box.current.children[active.start] as HTMLElement | undefined;
    if (row) box.current.scrollTo({ top: Math.max(row.offsetTop - 48, 0), behavior: "smooth" });
  }, [active]);
  return (
    <div className="overflow-hidden rounded-lg bg-screen shadow-sm">
      <div className="border-b border-white/10 px-4 py-2 font-mono text-xs text-phosphor/60">
        MAINFRAME TERMINAL
      </div>
      <pre ref={box} className="relative max-h-[34rem] overflow-auto p-4 font-mono text-[13px] leading-6 text-phosphor/90">
        {lines.map((line, i) => {
          const on = active && i >= active.start && i <= active.end;
          return (
            <div key={i} className={`flex transition-colors duration-700 ${on ? "bg-phosphor/15" : ""}`}>
              <span className="w-10 shrink-0 select-none pr-3 text-right text-phosphor/35">{i + 1}</span>
              <span className="whitespace-pre">{line || " "}</span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

function OutputLines({ lines, other }: { lines: string[] | null; other: string[] | null }) {
  if (!lines) return <p className="font-mono text-sm text-muted">no output</p>;
  return (
    <div className="font-mono text-sm">
      {lines.map((l, i) => (
        <div key={i} className={other && other[i] !== l ? "bg-ink/10 font-bold underline decoration-2 underline-offset-4 px-1" : "px-1"}>{l}</div>
      ))}
    </div>
  );
}

function RestlessSpirit({ spirit, names }: { spirit: Spirit; names: string[] }) {
  return (
    <div className="animate-rise rounded-lg border border-ink p-5">
      <p className="font-mono text-xs uppercase tracking-wider text-muted">Inputs</p>
      <p className="mt-1 font-mono text-sm">
        {spirit.inputs.map((v, i) => `${names[i] ?? `input ${i + 1}`} ${v}`).join("   ")}
      </p>
      <div className="mt-5 grid gap-6 sm:grid-cols-2">
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-wider text-muted">COBOL said</p>
          <OutputLines lines={spirit.cobol} other={spirit.python} />
        </div>
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-wider text-muted">Python said</p>
          <OutputLines lines={spirit.python} other={spirit.cobol} />
          {spirit.error && <p className="mt-2 font-mono text-xs text-muted">{spirit.error}</p>}
        </div>
      </div>
    </div>
  );
}

export default function Necromancer() {
  const [samples, setSamples] = useState<SampleSummary[]>([]);
  const [sampleId, setSampleId] = useState<string | null>(null);
  const [sample, setSample] = useState<Sample | null>(null);
  const [exhumed, setExhumed] = useState<Exhumed | null>(null);
  const [python, setPython] = useState<string | null>(null);
  const [result, setResult] = useState<SeanceResult | null>(null);
  const [cases, setCases] = useState(200);
  const [busy, setBusy] = useState<"" | "exhume" | "resurrect" | "seance">("");
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    listSamples()
      .then((s) => { setSamples(s); setSampleId(s[0]?.id ?? null); })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!sampleId) return;
    setSample(null); setExhumed(null); setPython(null); setResult(null); setError(null);
    getSample(sampleId).then(setSample).catch((e) => setError(e.message));
  }, [sampleId]);

  const ranges = useMemo(() => (sample ? paragraphRanges(sample.cobol) : []), [sample]);
  const activeRange = ranges.find((r) => r.name === hovered) ?? null;

  async function run<T>(kind: "exhume" | "resurrect" | "seance", fn: () => Promise<T>, done: (v: T) => void) {
    setBusy(kind); setError(null);
    try { done(await fn()); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }

  const inputNames: string[] = useMemo(() => sample?.inputs.map((f) => f.name) ?? [], [sample]);

  return (
    <main className="mx-auto max-w-6xl px-6 pb-40 sm:px-10">
      {/* Hero */}
      <section className="pb-32 pt-28 sm:pt-40">
        <p className="font-mono text-sm tracking-wide text-muted">NECROMANCER</p>
        <h1 className="headline animate-rise mt-6 text-[clamp(3.5rem,11vw,9rem)]">
          Bring dead COBOL<br />back to life.
        </h1>
        <p className="animate-rise mt-8 max-w-xl text-xl text-muted" style={{ animationDelay: "250ms" }}>
          Then prove it still behaves the same.
        </p>

        <div className="mt-14 flex flex-wrap gap-3" role="tablist" aria-label="Choose a program">
          {samples.map((s) => (
            <button
              key={s.id}
              role="tab"
              aria-selected={s.id === sampleId}
              onClick={() => setSampleId(s.id)}
              className={`rounded-full border px-5 py-2.5 text-sm font-medium transition-colors duration-500 ${
                s.id === sampleId ? "border-ink bg-ink text-paper" : "border-line hover:border-ink"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>
        {error && <p role="alert" className="mt-6 text-sm text-ink underline">{error}</p>}
      </section>

      {/* 01 Exhume */}
      <section className="border-t border-line py-28">
        <StepHeader n="01" title="Exhume" line="Read the old program the way it was written, then hear what it does in plain English." />
        <div className="grid gap-10 lg:grid-cols-2">
          <div>{sample ? <GreenScreen cobol={sample.cobol} active={activeRange} /> : <p className="text-muted">Loading…</p>}</div>
          <div>
            {!exhumed ? (
              <div>
                <p className="max-w-md text-muted">
                  {sample ? "Nothing is explained until you ask. The code on the left is the real file." : ""}
                </p>
                <div className="mt-6">
                  <ActionButton disabled={!sampleId || busy !== ""} onClick={() => run("exhume", () => exhume(sampleId!), setExhumed)}>
                    {busy === "exhume" ? "Exhuming" : "Exhume"}
                  </ActionButton>
                </div>
              </div>
            ) : (
              <div className="animate-rise">
                <p className="text-2xl leading-snug tracking-tight">{exhumed.summary}</p>
                <ul className="mt-10 divide-y divide-line border-y border-line">
                  {exhumed.paragraphs.map((p) => (
                    <li
                      key={p.name}
                      onMouseEnter={() => setHovered(p.name)}
                      onMouseLeave={() => setHovered(null)}
                      onFocus={() => setHovered(p.name)}
                      onBlur={() => setHovered(null)}
                      tabIndex={0}
                      className="py-5 outline-none"
                    >
                      <p className="font-mono text-sm">{p.name}</p>
                      <p className="mt-1 text-muted">{p.explanation}</p>
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-sm text-muted">Hover a paragraph to find it in the code.</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 02 Resurrect */}
      {exhumed && (
        <section className="animate-rise border-t border-line py-28">
          <StepHeader n="02" title="Resurrect" line="The same logic in modern Python. Money uses Decimal, never float, and cents are cut off exactly like the original." />
          {!python ? (
            <ActionButton disabled={busy !== ""} onClick={() => run("resurrect", () => resurrect(sampleId!), (v) => setPython(v.python))}>
              {busy === "resurrect" ? "Resurrecting" : "Resurrect"}
            </ActionButton>
          ) : (
            <div className="animate-rise">
              <div className="overflow-hidden rounded-lg border border-line bg-white">
                <div className="flex items-center justify-between border-b border-line px-4 py-2">
                  <span className="font-mono text-xs text-muted">translation.py (editable)</span>
                  <button
                    onClick={() => { setPython(introduceBug(python)); setResult(null); }}
                    className="font-mono text-xs underline underline-offset-4 hover:text-muted"
                  >
                    Introduce a bug
                  </button>
                </div>
                <textarea
                  value={python}
                  onChange={(e) => { setPython(e.target.value); setResult(null); }}
                  spellCheck={false}
                  aria-label="Python translation"
                  className="block h-[28rem] w-full resize-y bg-white p-4 font-mono text-[13px] leading-6 outline-none"
                />
              </div>
              <p className="mt-4 text-sm text-muted">
                Edit anything. The seance below tests whatever is in this box, not what we last generated.
              </p>
            </div>
          )}
        </section>
      )}

      {/* 03 Seance */}
      {python && (
        <section className="animate-rise border-t border-line py-28">
          <StepHeader n="03" title="Seance" line="Run the old program and the new one on the same inputs, over and over. A translation is only trusted if every answer matches." />
          <div className="flex flex-wrap items-center gap-6">
            <ActionButton disabled={busy !== ""} onClick={() => run("seance", () => seance(sampleId!, python, cases), setResult)}>
              {busy === "seance" ? "Running both programs" : "Hold the seance"}
            </ActionButton>
            <label className="flex items-center gap-3 text-sm text-muted">
              Inputs
              <select
                value={cases}
                onChange={(e) => setCases(Number(e.target.value))}
                className="rounded-full border border-line bg-paper px-4 py-2 text-ink"
              >
                {[50, 100, 200, 500].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
          </div>

          {result && (
            <div className="animate-rise mt-16">
              <p className="headline text-[clamp(4rem,12vw,10rem)]">
                {result.matched}<span className="text-muted"> / {result.cases_run}</span>
              </p>
              <p className="mt-4 text-2xl tracking-tight">
                {result.verified ? (
                  <>
                    <span className="mr-3 inline-block h-3 w-3 rounded-full bg-phosphor align-middle" aria-hidden />
                    Verified. Every answer matched.
                  </>
                ) : (
                  <>Not verified. {result.spirit_count} restless {result.spirit_count === 1 ? "spirit" : "spirits"} found.</>
                )}
              </p>
              {!result.verified && (
                <div className="mt-12 space-y-5">
                  <p className="text-muted">
                    Showing {Math.min(5, result.restless_spirits.length)} of {result.spirit_count}. Bold underlined lines differ.
                  </p>
                  {result.restless_spirits.slice(0, 5).map((s, i) => (
                    <RestlessSpirit key={i} spirit={s} names={inputNames} />
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <footer className="border-t border-line pt-10 text-sm text-muted">
        Built for Kiroween 2026. The original program and its translation are only ever shown as correct after a seance.
      </footer>
    </main>
  );
}
