const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SampleSummary = { id: string; name: string; summary: string };
export type InputSpec = { name: string; digits: number; scale: number; min: string; max: string };
export type Sample = SampleSummary & { cobol: string; python: string | null; inputs: InputSpec[] };
export type Paragraph = { name: string; explanation: string };
export type Exhumed = { summary: string; paragraphs: Paragraph[]; source: string };
export type Spirit = { inputs: string[]; cobol: string[]; python: string[] | null; error: string | null };
export type SeanceResult = {
  cases_run: number;
  matched: number;
  verified: boolean;
  spirit_count: number;
  restless_spirits: Spirit[];
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

export const listSamples = () => call<SampleSummary[]>("/api/samples");
export const getSample = (id: string) => call<Sample>(`/api/samples/${id}`);
export const exhume = (sample_id: string) => call<Exhumed>("/api/exhume", { sample_id });
export const resurrect = (sample_id: string) => call<{ python: string }>("/api/resurrect", { sample_id });
export const seance = (sample_id: string, python: string, cases: number) =>
  call<SeanceResult>("/api/seance", { sample_id, python, cases });
