const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SampleSummary = { id: string; name: string; summary: string };
export type InputSpec = { name: string; digits: number; scale: number; min: string; max: string };
export type Sample = SampleSummary & { cobol: string; python: string | null; inputs: InputSpec[] };
export type Paragraph = { name: string; explanation: string };
export type Exhumed = { summary: string; paragraphs: Paragraph[]; source: string };
export type Spirit = { inputs: string[]; cobol: string[] | null; python: string[] | null; error: string | null };
export type SeanceResult = {
  cases_run: number;
  matched: number;
  verified: boolean;
  spirit_count: number;
  restless_spirits: Spirit[];
  minimal_spirit: Spirit | null;
  boundaries_tested: string[];
  certificate: Record<string, unknown>;
};
export type Finding = { kind: string; where: string; title: string; detail: string };
export type Mutant = {
  kind: string;
  description: string;
  status: "caught" | "caught_on_stress" | "survived";
  example: Spirit | null;
};
export type Haunted = {
  total: number;
  caught: number;
  survived: number;
  cases_per_mutant: number;
  stress_cases: number;
  mutants: Mutant[];
};
export type Exorcised = {
  verified: boolean;
  python: string;
  result: SeanceResult;
  rounds: { attempt: number; matched: number; cases_run: number; spirit_count: number }[];
};

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return res.json();
}

export type Source = { sample_id: string } | { cobol: string };

export const listSamples = () => call<SampleSummary[]>("/api/samples");
export const getSample = (id: string) => call<Sample>(`/api/samples/${id}`);
export const inferInputs = (cobol: string) => call<{ inputs: InputSpec[] }>("/api/infer-inputs", { cobol });
export const exhume = (src: Source) => call<Exhumed>("/api/exhume", src);
export const resurrect = (src: Source) => call<{ python: string }>("/api/resurrect", src);
export const seance = (src: Source, python: string, cases: number, inputs?: InputSpec[]) =>
  call<SeanceResult>("/api/seance", { ...src, python, cases, ...(inputs ? { inputs } : {}) });
export const autopsy = (src: Source) => call<{ findings: Finding[] }>("/api/autopsy", src);
export const haunt = (src: Source, python: string, cases: number, inputs?: InputSpec[]) =>
  call<Haunted>("/api/haunt", { ...src, python, cases, ...(inputs ? { inputs } : {}) });
export const exorcise = (src: Source, python: string, cases: number, inputs?: InputSpec[]) =>
  call<Exorcised>("/api/exorcise", { ...src, python, cases, ...(inputs ? { inputs } : {}) });
