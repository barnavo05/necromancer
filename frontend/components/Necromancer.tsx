"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  autopsy, exhume, exorcise, getSample, haunt, inferInputs, listSamples, resurrect, seance,
  type Exhumed, type Finding, type Haunted, type InputSpec, type Sample, type SampleSummary,
  type SeanceResult, type Source, type Spirit,
} from "@/lib/api";

const CUSTOM = "__custom__";
const CUSTOM_HINT = `       IDENTIFICATION DIVISION.
       PROGRAM-ID. MYPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE   PIC X(20).
       01 WS-AMOUNT PIC 9(5)V99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-AMOUNT = FUNCTION NUMVAL(WS-LINE)
           DISPLAY "AMOUNT=" WS-AMOUNT
           STOP RUN.
`;
const PYTHON_STUB = `from decimal import Decimal


def main(lines):
    # lines are the stdin lines. Return the stdout lines.
    return []
`;

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
  if (!lines) return <p className="px-1 font-mono text-sm font-bold underline decoration-2 underline-offset-4">no output</p>;
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

function downloadCertificate(result: SeanceResult, name: string) {
  const blob = new Blob([JSON.stringify(result.certificate, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `necromancer-certificate-${name}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function differingLine(s: Spirit | null): string | null {
  if (!s || !s.cobol || !s.python) return s?.error ?? null;
  const i = s.cobol.findIndex((l, k) => l !== s.python![k]);
  return i < 0 ? null : `COBOL ${s.cobol[i]}   Python ${s.python[i]}`;
}

function AutopsyList({ findings }: { findings: Finding[] }) {
  if (!findings.length) return null;
  return (
    <div className="animate-rise mt-24">
      <p className="font-mono text-sm tracking-wide text-muted">AUTOPSY</p>
      <h3 className="headline mt-3 text-4xl sm:text-5xl">
        {findings.length} things in this program will bite a translation.
      </h3>
      <ul className="mt-10 grid gap-x-12 gap-y-8 sm:grid-cols-2">
        {findings.map((f, i) => (
          <li key={i} className="border-t border-line pt-4">
            <p className="font-mono text-xs uppercase tracking-wider text-muted">{f.where}</p>
            <p className="mt-2 text-lg font-bold tracking-tight">{f.title}</p>
            <p className="mt-1 text-muted">{f.detail}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HauntPanel({ haunted }: { haunted: Haunted }) {
  return (
    <div className="animate-rise mt-20 border-t border-line pt-16">
      <p className="font-mono text-sm tracking-wide text-muted">HAUNTED</p>
      <p className="headline mt-3 text-[clamp(3rem,9vw,7rem)]">
        {haunted.caught}<span className="text-muted"> / {haunted.total}</span>
      </p>
      <p className="mt-3 text-2xl tracking-tight">injected bugs caught by the seance.</p>
      <p className="mt-3 max-w-2xl text-muted">
        We broke the translation on purpose, one small change at a time, and ran the seance on each broken copy.
        {haunted.survived > 0 &&
          ` ${haunted.survived} survived even ${haunted.stress_cases} extra random inputs. That usually means the change did not alter the answer (for example > versus >= where both branches agree), or the difference hides in a very narrow range.`}
      </p>
      <ul className="mt-10 divide-y divide-line border-y border-line">
        {haunted.mutants.map((m, i) => (
          <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-4">
            <span className="font-mono text-sm">{m.description}</span>
            <span className={`font-mono text-sm ${m.status === "survived" ? "text-muted" : "font-bold"}`}>
              {m.status === "survived" ? "survived" : m.status === "caught_on_stress" ? "caught (extra inputs)" : "caught"}
              {m.example && differingLine(m.example) ? `, ${differingLine(m.example)}` : ""}
            </span>
          </li>
        ))}
      </ul>
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
  const [busy, setBusy] = useState<"" | "exhume" | "resurrect" | "seance" | "haunt" | "exorcise">("");
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [haunted, setHaunted] = useState<Haunted | null>(null);
  const [exorcism, setExorcism] = useState<string | null>(null);
  const [customCobol, setCustomCobol] = useState("");
  const [customInputs, setCustomInputs] = useState<InputSpec[] | null>(null);

  const isCustom = sampleId === CUSTOM;
  const cobolText = isCustom ? customCobol : sample?.cobol ?? "";
  const source: Source | null = isCustom ? (customCobol.trim() ? { cobol: customCobol } : null) : sampleId ? { sample_id: sampleId } : null;

  useEffect(() => {
    listSamples()
      .then((s) => { setSamples(s); setSampleId(s[0]?.id ?? null); })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!sampleId) return;
    setSample(null); setExhumed(null); setPython(null); setResult(null); setHaunted(null); setExorcism(null); setError(null);
    if (sampleId === CUSTOM) return;
    getSample(sampleId).then(setSample).catch((e) => setError(e.message));
  }, [sampleId]);

  const ranges = useMemo(() => paragraphRanges(cobolText), [cobolText]);
  const activeRange = ranges.find((r) => r.name === hovered) ?? null;

  async function run<T>(kind: "exhume" | "resurrect" | "seance" | "haunt" | "exorcise", fn: () => Promise<T>, done: (v: T) => void) {
    setBusy(kind); setError(null);
    try { done(await fn()); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }

  useEffect(() => {
    setFindings([]);
    if (!source) return;
    const t = setTimeout(() => { autopsy(source).then((r) => setFindings(r.findings)).catch(() => setFindings([])); }, isCustom ? 700 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sampleId, customCobol, sample]);

  const specInputs = isCustom ? customInputs : sample?.inputs ?? null;
  const inputNames: string[] = useMemo(() => specInputs?.map((f) => f.name) ?? [], [specInputs]);

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
          {samples.length > 0 && (
            <button
              role="tab"
              aria-selected={isCustom}
              onClick={() => setSampleId(CUSTOM)}
              className={`rounded-full border px-5 py-2.5 text-sm font-medium transition-colors duration-500 ${
                isCustom ? "border-ink bg-ink text-paper" : "border-dashed border-ink/40 hover:border-ink"
              }`}
            >
              Your own program
            </button>
          )}
        </div>
        {error && <p role="alert" className="mt-6 text-sm text-ink underline">{error}</p>}
      </section>

      {/* 01 Exhume */}
      <section className="border-t border-line py-28">
        <StepHeader n="01" title="Exhume" line="Read the old program the way it was written, then hear what it does in plain English." />
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            {isCustom ? (
              <div className="overflow-hidden rounded-lg bg-screen shadow-sm">
                <div className="border-b border-white/10 px-4 py-2 font-mono text-xs text-phosphor/60">
                  MAINFRAME TERMINAL (paste your COBOL)
                </div>
                <textarea
                  value={customCobol}
                  onChange={(e) => { setCustomCobol(e.target.value); setCustomInputs(null); setExhumed(null); setPython(null); setResult(null); }}
                  placeholder={CUSTOM_HINT}
                  spellCheck={false}
                  aria-label="Your COBOL program"
                  className="block h-[34rem] w-full resize-y bg-screen p-4 font-mono text-[13px] leading-6 text-phosphor/90 outline-none placeholder:text-phosphor/30"
                />
              </div>
            ) : sample ? (
              <GreenScreen cobol={sample.cobol} active={activeRange} />
            ) : (
              <p className="text-muted">Loading…</p>
            )}
          </div>
          <div>
            {!exhumed ? (
              <div>
                <p className="max-w-md text-muted">
                  {isCustom
                    ? "Paste a COBOL program that reads each input with ACCEPT into a text field, then FUNCTION NUMVAL on the next line. Find its inputs first, so the seance knows what to feed it."
                    : sample ? "Nothing is explained until you ask. The code on the left is the real file." : ""}
                </p>
                {isCustom && (
                  <div className="mt-6">
                    <ActionButton
                      quiet
                      disabled={!customCobol.trim() || busy !== ""}
                      onClick={() => { setError(null); inferInputs(customCobol).then((r) => setCustomInputs(r.inputs)).catch((e) => setError(e.message)); }}
                    >
                      Find inputs
                    </ActionButton>
                  </div>
                )}
                {isCustom && customInputs && (
                  <div className="mt-6 animate-rise">
                    <p className="mb-3 text-sm text-muted">
                      The seance will only generate inputs inside these ranges. COBOL silently overflows, so keep them safe.
                    </p>
                    <div className="divide-y divide-line border-y border-line">
                      {customInputs.map((f, i) => (
                        <div key={i} className="flex flex-wrap items-center gap-4 py-3 font-mono text-sm">
                          <span className="w-32">{f.name}</span>
                          {(["min", "max"] as const).map((k) => (
                            <label key={k} className="flex items-center gap-2 text-muted">
                              {k}
                              <input
                                value={f[k]}
                                inputMode="decimal"
                                aria-label={`${f.name} ${k}`}
                                onChange={(e) =>
                                  setCustomInputs(customInputs.map((x, j) => (j === i ? { ...x, [k]: e.target.value } : x)))
                                }
                                className="w-24 rounded border border-line bg-paper px-2 py-1 text-ink"
                              />
                            </label>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-6">
                  <ActionButton disabled={!source || busy !== ""} onClick={() => run("exhume", () => exhume(source!), setExhumed)}>
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
        <AutopsyList findings={findings} />
      </section>

      {/* 02 Resurrect */}
      {(exhumed || (isCustom && customInputs)) && (
        <section className="animate-rise border-t border-line py-28">
          <StepHeader n="02" title="Resurrect" line="The same logic in modern Python. Money uses Decimal, never float, and cents are cut off exactly like the original." />
          {!python ? (
            <div className="flex flex-wrap items-center gap-4">
              <ActionButton disabled={busy !== ""} onClick={() => run("resurrect", () => resurrect(source!), (v) => setPython(v.python))}>
                {busy === "resurrect" ? "Resurrecting" : "Resurrect"}
              </ActionButton>
              {isCustom && (
                <ActionButton quiet disabled={busy !== ""} onClick={() => setPython(PYTHON_STUB)}>
                  Write the Python myself
                </ActionButton>
              )}
            </div>
          ) : (
            <div className="animate-rise">
              <div className="overflow-hidden rounded-lg border border-line bg-white">
                <div className="flex items-center justify-between border-b border-line px-4 py-2">
                  <span className="font-mono text-xs text-muted">translation.py (editable)</span>
                  <button
                    onClick={() => { setPython(introduceBug(python)); setResult(null); setHaunted(null); setExorcism(null); }}
                    className="font-mono text-xs underline underline-offset-4 hover:text-muted"
                  >
                    Introduce a bug
                  </button>
                </div>
                <textarea
                  value={python}
                  onChange={(e) => { setPython(e.target.value); setResult(null); setHaunted(null); setExorcism(null); }}
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
            <ActionButton
              disabled={busy !== "" || (isCustom && !customInputs)}
              onClick={() => run("seance", () => seance(source!, python, cases, isCustom ? customInputs! : undefined), setResult)}
            >
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

          {isCustom && !customInputs && (
            <p className="mt-4 text-sm text-muted">Find your program's inputs in step 01 first.</p>
          )}
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
              {result.boundaries_tested.length > 0 && (
                <p className="mt-4 max-w-2xl font-mono text-sm text-muted">
                  Edges tested on purpose: {result.boundaries_tested.join(", ")} (and one step either side). These constants were read straight out of the COBOL.
                </p>
              )}

              {result.verified ? (
                <div className="mt-10 flex flex-wrap gap-3">
                  <ActionButton disabled={busy !== "" || (isCustom && !customInputs)} onClick={() => run("haunt", () => haunt(source!, python, 150, isCustom ? customInputs! : undefined), setHaunted)}>
                    {busy === "haunt" ? "Haunting" : "Haunt the translation"}
                  </ActionButton>
                  <ActionButton quiet onClick={() => downloadCertificate(result, sampleId ?? "program")}>
                    Download certificate
                  </ActionButton>
                </div>
              ) : (
                <div className="mt-12 space-y-8">
                  {result.minimal_spirit && (
                    <div className="animate-rise">
                      <p className="font-mono text-sm tracking-wide text-muted">SMALLEST FAILING INPUT</p>
                      <p className="mt-2 max-w-2xl text-muted">
                        Every failure was shrunk to the simplest case that still disagrees. Start here.
                      </p>
                      <div className="mt-4">
                        <RestlessSpirit spirit={result.minimal_spirit} names={inputNames} />
                      </div>
                    </div>
                  )}
                  <div className="flex flex-wrap items-center gap-4">
                    <ActionButton disabled={busy !== "" || (isCustom && !customInputs)} onClick={() => run("exorcise", () => exorcise(source!, python, cases, isCustom ? customInputs! : undefined), (r) => {
                      setPython(r.python); setResult(r.result); setHaunted(null);
                      setExorcism(`${r.verified ? "Exorcised" : "Still haunted"} after ${r.rounds.length} ${r.rounds.length === 1 ? "round" : "rounds"}: ${r.rounds.map((x) => `${x.matched}/${x.cases_run}`).join(" then ")}.`);
                    })}>
                      {busy === "exorcise" ? "Exorcising" : "Exorcise"}
                    </ActionButton>
                    <p className="max-w-md text-sm text-muted">The model reads the restless spirits, fixes the Python, and the seance runs again. Needs the server API key.</p>
                  </div>
                  <p className="text-muted">
                    Showing {Math.min(5, result.restless_spirits.length)} of {result.spirit_count}. Bold underlined lines differ.
                  </p>
                  {result.restless_spirits.slice(0, 5).map((s, i) => (
                    <RestlessSpirit key={i} spirit={s} names={inputNames} />
                  ))}
                </div>
              )}
              {exorcism && <p className="animate-rise mt-8 font-mono text-sm">{exorcism}</p>}
              {haunted && <HauntPanel haunted={haunted} />}
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
