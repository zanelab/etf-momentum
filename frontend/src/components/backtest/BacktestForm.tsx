import { useMemo, useState } from "react";

import type { BacktestRequest, RebalanceFreq } from "@/api/backtest";
import type { EtfItem } from "@/api/etfs";
import type { FormErrors } from "@/stores/backtest-store";

export interface BacktestFormProps {
  etfs: EtfItem[];
  etfsLoading: boolean;
  etfsError: string | null;
  disabled?: boolean;
  formErrors?: FormErrors;
  onSubmit: (req: BacktestRequest) => void;
}

interface ValidationErrors {
  etf_pool?: string;
  start?: string;
  end?: string;
  initial_cash?: string;
  lookback?: string;
  skip?: string;
  top_n?: string;
}

interface FormState {
  etfPool: string[];
  start: string;
  end: string;
  initialCash: string;
  lookback: string;
  skip: string;
  topN: string;
  rebalanceFreq: RebalanceFreq;
}

const INITIAL_STATE: FormState = {
  etfPool: [],
  start: "",
  end: "",
  initialCash: "100000",
  lookback: "252",
  skip: "21",
  topN: "5",
  rebalanceFreq: "monthly",
};

function toNumber(value: string): number | null {
  if (value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function validate(state: FormState): ValidationErrors {
  const errors: ValidationErrors = {};
  if (state.etfPool.length === 0) {
    errors.etf_pool = "请至少选择一只 ETF";
  }
  if (!state.start) errors.start = "起始日期不能为空";
  if (!state.end) errors.end = "结束日期不能为空";
  if (state.start && state.end && state.start >= state.end) {
    errors.end = "结束日期必须晚于起始日期";
  }
  const cash = toNumber(state.initialCash);
  if (cash === null || cash <= 0) {
    errors.initial_cash = "初始资金必须 > 0";
  }
  const lookback = toNumber(state.lookback);
  if (lookback === null || lookback < 1) {
    errors.lookback = "回看天数必须 >= 1";
  }
  const skip = toNumber(state.skip);
  if (skip === null || skip < 0) {
    errors.skip = "缓冲天数必须 >= 0";
  }
  const topN = toNumber(state.topN);
  if (topN === null || topN < 1) {
    errors.top_n = "Top N 必须 >= 1";
  }
  return errors;
}

function toRequest(state: FormState): BacktestRequest {
  return {
    etf_pool: state.etfPool,
    start: state.start,
    end: state.end,
    initial_cash: state.initialCash,
    lookback: toNumber(state.lookback) ?? 252,
    skip: toNumber(state.skip) ?? 21,
    top_n: toNumber(state.topN) ?? 5,
    rebalance_freq: state.rebalanceFreq,
  };
}

export function BacktestForm({
  etfs,
  etfsLoading,
  etfsError,
  disabled = false,
  formErrors = {},
  onSubmit,
}: BacktestFormProps) {
  const [state, setState] = useState<FormState>(INITIAL_STATE);
  const [localErrors, setLocalErrors] = useState<ValidationErrors>({});

  const toggleEtf = (code: string) => {
    setState((prev) => {
      const next = prev.etfPool.includes(code)
        ? prev.etfPool.filter((c) => c !== code)
        : [...prev.etfPool, code];
      return { ...prev, etfPool: next };
    });
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const errors = validate(state);
    setLocalErrors(errors);
    if (Object.keys(errors).length > 0) return;
    onSubmit(toRequest(state));
  };

  const showEtfError = localErrors.etf_pool ?? formErrors.etf_pool;
  const fieldError = (key: keyof ValidationErrors): string | undefined => {
    return localErrors[key] ?? formErrors[key as keyof FormErrors];
  };

  const submitDisabled = useMemo(() => {
    return disabled || etfsLoading || etfsError !== null;
  }, [disabled, etfsLoading, etfsError]);

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-lg border bg-card p-6 shadow-sm"
      data-testid="backtest-form"
    >
      <section>
        <header className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">ETF 池</h2>
          <span className="text-sm text-muted-foreground" data-testid="pool-count">
            已选 {state.etfPool.length} / {etfs.length}
          </span>
        </header>

        {etfsLoading && (
          <div className="text-sm text-muted-foreground">ETF 字典加载中…</div>
        )}

        {etfsError && (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            ETF 字典加载失败：{etfsError}
          </div>
        )}

        {!etfsLoading && !etfsError && etfs.length === 0 && (
          <div className="text-sm text-muted-foreground">暂无 ETF 可选</div>
        )}

        {!etfsLoading && !etfsError && etfs.length > 0 && (
          <div
            className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
            data-testid="pool-grid"
          >
            {etfs.map((etf) => {
              const checked = state.etfPool.includes(etf.code);
              return (
                <label
                  key={etf.code}
                  className={`flex cursor-pointer items-center gap-2 rounded-md border p-2 text-sm transition-colors ${
                    checked ? "border-primary bg-primary/5" : "border-border bg-background"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEtf(etf.code)}
                    disabled={submitDisabled}
                    className="h-4 w-4 accent-primary"
                    data-testid={`pool-${etf.code}`}
                  />
                  <span className="flex-1 truncate">
                    <span className="font-mono text-xs text-muted-foreground">{etf.code}</span>
                    <span className="ml-2">{etf.name}</span>
                  </span>
                </label>
              );
            })}
          </div>
        )}

        {showEtfError && (
          <p className="mt-2 text-sm text-rose-600" data-testid="error-etf_pool">
            {showEtfError}
          </p>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Field
          label="起始日期"
          type="date"
          value={state.start}
          onChange={(v) => setState((s) => ({ ...s, start: v }))}
          error={fieldError("start")}
          disabled={submitDisabled}
          testId="field-start"
        />
        <Field
          label="结束日期"
          type="date"
          value={state.end}
          onChange={(v) => setState((s) => ({ ...s, end: v }))}
          error={fieldError("end")}
          disabled={submitDisabled}
          testId="field-end"
        />
        <Field
          label="初始资金"
          type="number"
          value={state.initialCash}
          onChange={(v) => setState((s) => ({ ...s, initialCash: v }))}
          error={fieldError("initial_cash")}
          disabled={submitDisabled}
          testId="field-initial_cash"
        />
        <Field
          label="回看天数 (lookback)"
          type="number"
          value={state.lookback}
          onChange={(v) => setState((s) => ({ ...s, lookback: v }))}
          error={fieldError("lookback")}
          disabled={submitDisabled}
          testId="field-lookback"
        />
        <Field
          label="缓冲天数 (skip)"
          type="number"
          value={state.skip}
          onChange={(v) => setState((s) => ({ ...s, skip: v }))}
          error={fieldError("skip")}
          disabled={submitDisabled}
          testId="field-skip"
        />
        <Field
          label="Top N"
          type="number"
          value={state.topN}
          onChange={(v) => setState((s) => ({ ...s, topN: v }))}
          error={fieldError("top_n")}
          disabled={submitDisabled}
          testId="field-top_n"
        />
        <div>
          <label className="mb-1 block text-sm font-medium">调仓频率</label>
          <select
            value={state.rebalanceFreq}
            onChange={(e) =>
              setState((s) => ({ ...s, rebalanceFreq: e.target.value as RebalanceFreq }))
            }
            disabled={submitDisabled}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            data-testid="field-rebalance_freq"
          >
            <option value="monthly">每月</option>
            <option value="quarterly">每季度</option>
          </select>
        </div>
      </section>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitDisabled}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="submit-button"
        >
          {disabled && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground" />
          )}
          {disabled ? "回测中…" : "提交回测"}
        </button>
      </div>
    </form>
  );
}

interface FieldProps {
  label: string;
  type: "date" | "number" | "text";
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  testId: string;
}

function Field({ label, type, value, onChange, error, disabled, testId }: FieldProps) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm disabled:opacity-50"
        data-testid={testId}
      />
      {error && (
        <p className="mt-1 text-sm text-rose-600" data-testid={`error-${testId.replace("field-", "")}`}>
          {error}
        </p>
      )}
    </div>
  );
}
