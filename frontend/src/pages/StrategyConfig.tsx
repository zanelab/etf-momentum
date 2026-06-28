// Strategy parameters editor (form for known keys).
import { useEffect, useState } from "react";

import { useStrategy, useUpdateStrategy } from "@/api/hooks";

const FIELDS: { key: string; label: string; type: "int" | "float" | "bool" }[] = [
  { key: "stock_sum", label: "持仓数量", type: "int" },
  { key: "min_money", label: "最小交易金额", type: "int" },
  { key: "momentum_days", label: "动量天数", type: "int" },
  { key: "volume_lookback", label: "量比回看天数", type: "int" },
  { key: "volume_threshold", label: "量比阈值", type: "float" },
  { key: "ma_short", label: "短期均线", type: "int" },
  { key: "ma_long", label: "长期均线", type: "int" },
  { key: "enable_volume_check", label: "启用量比过滤", type: "bool" },
  { key: "enable_ma_filter", label: "启用双均线过滤", type: "bool" },
  { key: "enable_industry_diverse", label: "启用行业分散", type: "bool" },
  { key: "stop_loss_ratio", label: "止损比例", type: "float" },
  { key: "defensive_etf", label: "防御 ETF code", type: "int" }, // treated as string below
];

export default function StrategyConfig() {
  const strategy = useStrategy();
  const update = useUpdateStrategy();
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (strategy.data?.params) setDraft(strategy.data.params);
  }, [strategy.data]);

  if (strategy.isLoading) return <p>加载中…</p>;
  if (strategy.error) return <p className="text-red-600">加载失败</p>;

  const set = (key: string, value: unknown) => {
    setDirty(true);
    setDraft((d) => ({ ...d, [key]: value }));
  };

  const renderField = (key: string, _label: string, type: string) => {
    const value = draft[key];
    if (type === "bool") {
      return (
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => set(key, e.target.checked)}
        />
      );
    }
    if (key === "defensive_etf") {
      return (
        <input
          className="w-40 rounded border px-2 py-1 text-sm"
          value={String(value ?? "")}
          onChange={(e) => set(key, e.target.value)}
        />
      );
    }
    return (
      <input
        type="number"
        className="w-32 rounded border px-2 py-1 text-sm"
        value={value === undefined || value === null ? "" : Number(value)}
        onChange={(e) =>
          set(key, type === "float" ? Number(e.target.value) : parseInt(e.target.value, 10))
        }
      />
    );
  };

  return (
    <section>
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">策略参数</h2>
        <button
          className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
          disabled={!dirty || update.isPending}
          onClick={() => update.mutate(draft, { onSuccess: () => setDirty(false) })}
        >
          保存
        </button>
      </header>
      <div className="grid max-w-xl grid-cols-[200px_1fr] gap-3">
        {FIELDS.map((f) => (
          <FragmentRow key={f.key} label={f.label}>
            {renderField(f.key, f.label, f.type)}
          </FragmentRow>
        ))}
      </div>
    </section>
  );
}

function FragmentRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <span className="py-1.5">{label}</span>
      <span className="py-1.5">{children}</span>
    </>
  );
}
