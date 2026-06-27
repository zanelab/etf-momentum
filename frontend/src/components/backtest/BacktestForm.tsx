import { useMemo, useState } from "react";

import type { BacktestRequest, RebalanceFreq } from "@/api/backtest";
import type { EtfItem } from "@/api/etfs";
import type { EtfPoolSummary, EtfPoolDetail } from "@/api/pools";
import { EtfPickerGrid } from "@/components/pools/EtfPickerGrid";
import type { FormErrors } from "@/stores/backtest-store";

export type PoolMode = "pool" | "custom";

export interface BacktestFormProps {
  etfs: EtfItem[];
  etfsLoading: boolean;
  etfsError: string | null;
  pools?: EtfPoolSummary[];
  poolsLoading?: boolean;
  poolsError?: string | null;
  poolDetail?: EtfPoolDetail | null;
  poolDetailLoading?: boolean;
  poolsLink?: string;
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
  mode: PoolMode;
  selectedPoolId: number | null;
  customEtfPool: string[];
  start: string;
  end: string;
  initialCash: string;
  lookback: string;
  skip: string;
  topN: string;
  rebalanceFreq: RebalanceFreq;
}

const INITIAL_STATE: FormState = {
  mode: "custom",
  selectedPoolId: null,
  customEtfPool: [],
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

function validate(state: FormState, poolSize: number): ValidationErrors {
  const errors: ValidationErrors = {};
  if (poolSize === 0) {
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

function toRequest(state: FormState, poolCodes: string[]): BacktestRequest {
  const base: BacktestRequest = {
    etf_pool: poolCodes,
    start: state.start,
    end: state.end,
    initial_cash: state.initialCash,
    lookback: toNumber(state.lookback) ?? 252,
    skip: toNumber(state.skip) ?? 21,
    top_n: toNumber(state.topN) ?? 5,
    rebalance_freq: state.rebalanceFreq,
  };
  if (state.mode === "pool" && state.selectedPoolId !== null) {
    base.pool_id = state.selectedPoolId;
  } else {
    base.pool_id = null;
  }
  return base;
}

export function BacktestForm({
  etfs,
  etfsLoading,
  etfsError,
  pools = [],
  poolsLoading = false,
  poolsError = null,
  poolDetail = null,
  poolDetailLoading = false,
  poolsLink = "/pools",
  disabled = false,
  formErrors = {},
  onSubmit,
}: BacktestFormProps) {
  const [state, setState] = useState<FormState>(INITIAL_STATE);
  const [localErrors, setLocalErrors] = useState<ValidationErrors>({});

  const poolCodes = useMemo(() => {
    if (state.mode !== "pool") return state.customEtfPool;
    if (poolDetail && poolDetail.id === state.selectedPoolId) {
      return poolDetail.members.map((m) => m.code);
    }
    return [];
  }, [state.mode, state.customEtfPool, state.selectedPoolId, poolDetail]);

  const effectiveTotal = poolCodes.length;

  const switchMode = (next: PoolMode) => {
    if (next === state.mode) return;
    if (effectiveTotal > 0) {
      const ok = window.confirm(
        "切换模式将忽略当前 ETF 选择，确认继续？",
      );
      if (!ok) return;
    }
    setState((prev) => ({
      ...prev,
      mode: next,
      selectedPoolId: next === "pool" ? prev.selectedPoolId : null,
    }));
    setLocalErrors((prev) => ({ ...prev, etf_pool: undefined }));
  };

  const selectPool = (id: number | null) => {
    setState((prev) => ({ ...prev, selectedPoolId: id }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const errors = validate(state, effectiveTotal);
    setLocalErrors(errors);
    if (Object.keys(errors).length > 0) return;
    onSubmit(toRequest(state, poolCodes));
  };

  const submitDisabled = useMemo(() => {
    return disabled || etfsLoading || etfsError !== null;
  }, [disabled, etfsLoading, etfsError]);

  const showEtfError = localErrors.etf_pool ?? formErrors.etf_pool;
  const fieldError = (key: keyof ValidationErrors): string | undefined => {
    return localErrors[key] ?? formErrors[key as keyof FormErrors];
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-lg border bg-card p-6 shadow-sm"
      data-testid="backtest-form"
    >
      <section>
        <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2" data-testid="mode-toggle">
            <button
              type="button"
              onClick={() => switchMode("pool")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                state.mode === "pool"
                  ? "bg-primary text-primary-foreground"
                  : "border bg-background hover:bg-muted"
              }`}
              data-testid="mode-pool"
              disabled={submitDisabled}
            >
              使用策略池
            </button>
            <button
              type="button"
              onClick={() => switchMode("custom")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                state.mode === "custom"
                  ? "bg-primary text-primary-foreground"
                  : "border bg-background hover:bg-muted"
              }`}
              data-testid="mode-custom"
              disabled={submitDisabled}
            >
              自定义
            </button>
          </div>
          <span className="text-sm text-muted-foreground" data-testid="pool-count">
            已选 {effectiveTotal} / {etfs.length}
          </span>
        </header>

        {state.mode === "pool" && (
          <PoolModeArea
            pools={pools}
            poolsLoading={poolsLoading}
            poolsError={poolsError}
            poolDetail={poolDetail}
            poolDetailLoading={poolDetailLoading}
            selectedPoolId={state.selectedPoolId}
            onSelectPool={selectPool}
            etfs={etfs}
            etfsLoading={etfsLoading}
            etfsError={etfsError}
            poolCodes={poolCodes}
            disabled={submitDisabled}
            poolsLink={poolsLink}
            testId="backtest-pool-mode"
          />
        )}

        {state.mode === "custom" && (
          <EtfPickerGrid
            etfs={etfs}
            selected={state.customEtfPool}
            onChange={(next) =>
              setState((prev) => ({ ...prev, customEtfPool: next }))
            }
            disabled={submitDisabled}
            loading={etfsLoading}
            error={etfsError}
            testId="backtest-picker"
          />
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

interface PoolModeAreaProps {
  pools: EtfPoolSummary[];
  poolsLoading: boolean;
  poolsError: string | null;
  poolDetail: EtfPoolDetail | null;
  poolDetailLoading: boolean;
  selectedPoolId: number | null;
  onSelectPool: (id: number | null) => void;
  etfs: EtfItem[];
  etfsLoading: boolean;
  etfsError: string | null;
  poolCodes: string[];
  disabled: boolean;
  poolsLink: string;
  testId: string;
}

function PoolModeArea({
  pools,
  poolsLoading,
  poolsError,
  poolDetail,
  poolDetailLoading,
  selectedPoolId,
  onSelectPool,
  etfs,
  etfsLoading,
  etfsError,
  poolCodes,
  disabled,
  poolsLink,
  testId,
}: PoolModeAreaProps) {
  const retry = (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className="mt-2 rounded-md border bg-white px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100"
      data-testid={`${testId}-retry`}
    >
      重试
    </button>
  );

  return (
    <div className="space-y-3" data-testid={testId}>
      <div className="flex flex-wrap items-center gap-3">
        <label
          htmlFor={`${testId}-select`}
          className="text-sm font-medium"
        >
          策略池
        </label>
        <select
          id={`${testId}-select`}
          value={selectedPoolId === null ? "" : String(selectedPoolId)}
          onChange={(e) =>
            onSelectPool(e.target.value === "" ? null : Number(e.target.value))
          }
          disabled={disabled || poolsLoading || poolsError !== null}
          className="min-w-[200px] rounded-md border bg-background px-3 py-1.5 text-sm shadow-sm disabled:opacity-50"
          data-testid={`${testId}-select`}
        >
          <option value="">请选择…</option>
          {pools.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}（{p.member_count} 只）
            </option>
          ))}
        </select>
        {poolsLoading && (
          <span
            className="text-xs text-muted-foreground"
            data-testid={`${testId}-loading`}
          >
            加载策略池…
          </span>
        )}
        {poolsError && !poolsLoading && (
          <span
            className="text-xs text-rose-600"
            data-testid={`${testId}-error`}
          >
            加载失败：{poolsError}
            {retry}
          </span>
        )}
        {!poolsLoading && !poolsError && pools.length === 0 && (
          <span
            className="text-xs text-muted-foreground"
            data-testid={`${testId}-empty`}
          >
            暂无策略池，
            <a
              href={poolsLink}
              className="text-primary hover:underline"
              data-testid={`${testId}-link`}
            >
              前往创建
            </a>
          </span>
        )}
      </div>

      {selectedPoolId !== null && poolDetailLoading && (
        <div
          className="flex items-center gap-2 text-sm text-muted-foreground"
          data-testid={`${testId}-detail-loading`}
        >
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-primary" />
          加载池成员…
        </div>
      )}

      {selectedPoolId !== null && !poolDetailLoading && poolDetail && (
        <EtfPickerGrid
          etfs={etfs}
          selected={poolCodes}
          onChange={() => {
            /* locked: pool controls selection */
          }}
          locked
          disabled={disabled}
          loading={etfsLoading}
          error={etfsError}
          testId={`${testId}-picker`}
        />
      )}
    </div>
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
