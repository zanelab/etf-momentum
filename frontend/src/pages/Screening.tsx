// Today's screening targets — quick visibility into the filter output.
import { useScreeningToday } from "@/api/hooks";

export default function Screening() {
  const screening = useScreeningToday();
  if (screening.isLoading) return <p>加载中…</p>;
  if (screening.error) return <p className="text-red-600">加载失败</p>;
  const data = screening.data;
  if (!data) return null;

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-lg font-semibold">当日筛选 · {data.as_of}</h2>
        <p className="text-sm text-muted-foreground">
          共 {data.targets.length} 个目标 ETF
        </p>
      </header>
      <div className="flex flex-wrap gap-2">
        {data.targets.length === 0 ? (
          <p className="text-sm text-muted-foreground">无目标（将切换防御模式）</p>
        ) : (
          data.targets.map((code) => (
            <span
              key={code}
              className="rounded border bg-emerald-50 px-3 py-1 font-mono text-sm text-emerald-900"
            >
              {code}
            </span>
          ))
        )}
      </div>
    </section>
  );
}
