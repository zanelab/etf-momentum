import { useMemo, useState } from "react";

import type { EtfItem } from "@/api/etfs";

export interface EtfPickerGridProps {
  etfs: EtfItem[];
  selected: string[];
  onChange: (selected: string[]) => void;
  locked?: boolean;
  disabled?: boolean;
  loading?: boolean;
  error?: string | null;
  showLimit?: number;
  emptyMessage?: string;
  testId?: string;
}

export function EtfPickerGrid({
  etfs,
  selected,
  onChange,
  locked = false,
  disabled = false,
  loading = false,
  error = null,
  showLimit = 12,
  emptyMessage = "暂无 ETF 可选",
  testId = "etf-picker",
}: EtfPickerGridProps) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return etfs;
    return etfs.filter(
      (etf) =>
        etf.code.toLowerCase().includes(q) ||
        etf.name.toLowerCase().includes(q) ||
        (etf.category?.toLowerCase().includes(q) ?? false),
    );
  }, [etfs, query]);

  const visible = useMemo(() => {
    if (expanded || filtered.length <= showLimit) return filtered;
    return filtered.slice(0, showLimit);
  }, [filtered, expanded, showLimit]);

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const toggle = (code: string) => {
    if (locked || disabled) return;
    const next = selectedSet.has(code)
      ? selected.filter((c) => c !== code)
      : [...selected, code];
    onChange(next);
  };

  const hiddenCount = filtered.length - visible.length;

  return (
    <div data-testid={testId}>
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setExpanded(false);
            }}
            placeholder="搜索 代码 / 名称 / 类别"
            disabled={disabled || loading}
            className="w-56 rounded-md border bg-background px-3 py-1.5 text-sm shadow-sm disabled:opacity-50"
            data-testid={`${testId}-search`}
          />
          <span
            className="text-sm text-muted-foreground"
            data-testid={`${testId}-count`}
          >
            已选 {selected.length} / {etfs.length}
          </span>
          {locked && (
            <span
              className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              data-testid={`${testId}-locked-badge`}
            >
              锁定
            </span>
          )}
        </div>
      </header>

      {loading && (
        <div className="text-sm text-muted-foreground" data-testid={`${testId}-loading`}>
          ETF 字典加载中…
        </div>
      )}

      {error && !loading && (
        <div
          className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
          data-testid={`${testId}-error`}
        >
          ETF 字典加载失败：{error}
        </div>
      )}

      {!loading && !error && etfs.length === 0 && (
        <div className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
          {emptyMessage}
        </div>
      )}

      {!loading && !error && etfs.length > 0 && filtered.length === 0 && (
        <div className="text-sm text-muted-foreground" data-testid={`${testId}-no-match`}>
          没有匹配的 ETF
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <>
          <div
            className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
            data-testid={`${testId}-grid`}
          >
            {visible.map((etf) => {
              const checked = selectedSet.has(etf.code);
              const isDisabled = locked || disabled;
              return (
                <label
                  key={etf.code}
                  className={`flex cursor-pointer items-center gap-2 rounded-md border p-2 text-sm transition-colors ${
                    checked
                      ? "border-primary bg-primary/5"
                      : "border-border bg-background"
                  } ${isDisabled ? "cursor-not-allowed opacity-70" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(etf.code)}
                    disabled={isDisabled}
                    className="h-4 w-4 accent-primary"
                    data-testid={`${testId}-${etf.code}`}
                  />
                  <span className="flex-1 truncate">
                    <span className="font-mono text-xs text-muted-foreground">
                      {etf.code}
                    </span>
                    <span className="ml-2">{etf.name}</span>
                  </span>
                </label>
              );
            })}
          </div>

          {hiddenCount > 0 && (
            <div className="mt-2 text-center">
              <button
                type="button"
                onClick={() => setExpanded(true)}
                className="text-sm text-primary hover:underline"
                data-testid={`${testId}-show-more`}
              >
                显示剩余 {hiddenCount} 只
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
