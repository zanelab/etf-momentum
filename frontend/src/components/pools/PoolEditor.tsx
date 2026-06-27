import { useMemo, useState } from "react";

import type { EtfItem } from "@/api/etfs";
import type { AsyncStatus } from "@/stores/pools-store";
import { EtfPickerGrid } from "@/components/pools/EtfPickerGrid";

export interface PoolEditorProps {
  mode: "create" | "edit";
  initialName?: string;
  initialDescription?: string | null;
  initialCodes?: string[];
  etfs: EtfItem[];
  etfsLoading: boolean;
  etfsError: string | null;
  submitStatus: AsyncStatus;
  submitError: string | null;
  formErrors?: { name?: string; etf_codes?: string };
  onSave: (req: { name: string; description: string | null; etf_codes: string[] }) => void;
  onCancel: () => void;
  testId?: string;
}

interface FormState {
  name: string;
  description: string;
  selected: string[];
}

export function PoolEditor({
  mode,
  initialName = "",
  initialDescription = "",
  initialCodes = [],
  etfs,
  etfsLoading,
  etfsError,
  submitStatus,
  submitError,
  formErrors = {},
  onSave,
  onCancel,
  testId = "pool-editor",
}: PoolEditorProps) {
  const [state, setState] = useState<FormState>(() => ({
    name: initialName,
    description: initialDescription ?? "",
    selected: initialCodes,
  }));

  const nameError = formErrors.name;
  const codesError = formErrors.etf_codes;

  const localNameError = useMemo(() => {
    if (state.name.trim() === "") return "池名称不能为空";
    return null;
  }, [state.name]);

  const localCodesError = useMemo(() => {
    if (state.selected.length === 0) return "请至少选择一只 ETF";
    return null;
  }, [state.selected]);

  const initialSet = useMemo(() => new Set(initialCodes), [initialCodes]);
  const currentSet = useMemo(() => new Set(state.selected), [state.selected]);

  const addedCodes = useMemo(
    () => state.selected.filter((c) => !initialSet.has(c)),
    [state.selected, initialSet],
  );
  const removedCodes = useMemo(
    () => initialCodes.filter((c) => !currentSet.has(c)),
    [initialCodes, currentSet],
  );
  const hasDiff = addedCodes.length > 0 || removedCodes.length > 0;

  const submitting = submitStatus === "loading";

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (localNameError || localCodesError) return;
    onSave({
      name: state.name.trim(),
      description: state.description.trim() === "" ? null : state.description.trim(),
      etf_codes: state.selected,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-lg border bg-card p-6 shadow-sm"
      data-testid={testId}
    >
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {mode === "create" ? "新建策略池" : `编辑：${initialName || ""}`}
        </h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="rounded-md border bg-background px-3 py-1.5 text-sm font-medium shadow-sm hover:bg-muted disabled:opacity-50"
            data-testid={`${testId}-cancel`}
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting || !!localNameError || !!localCodesError}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            data-testid={`${testId}-save`}
          >
            {submitting && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground" />
            )}
            {mode === "create" ? "创建" : "保存"}
          </button>
        </div>
      </header>

      <section>
        <label
          htmlFor={`${testId}-name`}
          className="mb-1 block text-sm font-medium"
        >
          池名称
        </label>
        <input
          id={`${testId}-name`}
          type="text"
          value={state.name}
          onChange={(e) => setState((s) => ({ ...s, name: e.target.value }))}
          disabled={submitting}
          placeholder="例如：宽基核心"
          className="w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm disabled:opacity-50"
          data-testid={`${testId}-name`}
        />
        {(nameError ?? localNameError) && (
          <p
            className="mt-1 text-sm text-rose-600"
            data-testid={`${testId}-error-name`}
          >
            {nameError ?? localNameError}
          </p>
        )}
      </section>

      <section>
        <label
          htmlFor={`${testId}-description`}
          className="mb-1 block text-sm font-medium"
        >
          描述 <span className="text-xs text-muted-foreground">(可选)</span>
        </label>
        <textarea
          id={`${testId}-description`}
          value={state.description}
          onChange={(e) =>
            setState((s) => ({ ...s, description: e.target.value }))
          }
          disabled={submitting}
          rows={2}
          placeholder="一句话描述这个池的用途"
          className="w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm disabled:opacity-50"
          data-testid={`${testId}-description`}
        />
      </section>

      <section>
        <label className="mb-1 block text-sm font-medium">ETF 成员</label>
        <EtfPickerGrid
          etfs={etfs}
          selected={state.selected}
          onChange={(next) => setState((s) => ({ ...s, selected: next }))}
          disabled={submitting}
          loading={etfsLoading}
          error={etfsError}
          testId={`${testId}-picker`}
        />
        {(codesError ?? localCodesError) && (
          <p
            className="mt-2 text-sm text-rose-600"
            data-testid={`${testId}-error-etf_codes`}
          >
            {codesError ?? localCodesError}
          </p>
        )}
      </section>

      {hasDiff && mode === "edit" && (
        <section
          className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm"
          data-testid={`${testId}-diff`}
        >
          <div className="font-medium text-amber-800">变更摘要</div>
          {addedCodes.length > 0 && (
            <div className="mt-1 text-amber-700">
              新增 {addedCodes.length} 只：
              <span className="font-mono text-xs">{addedCodes.join(", ")}</span>
            </div>
          )}
          {removedCodes.length > 0 && (
            <div className="mt-1 text-amber-700">
              移除 {removedCodes.length} 只：
              <span className="font-mono text-xs">{removedCodes.join(", ")}</span>
            </div>
          )}
        </section>
      )}

      {hasDiff && mode === "create" && state.selected.length > 0 && (
        <section
          className="rounded-md border bg-muted/40 p-3 text-sm"
          data-testid={`${testId}-summary`}
        >
          将创建包含 {state.selected.length} 只 ETF 的策略池
        </section>
      )}

      {submitStatus === "error" && submitError && !nameError && !codesError && (
        <p
          className="text-sm text-rose-600"
          data-testid={`${testId}-error-submit`}
        >
          {submitError}
        </p>
      )}
    </form>
  );
}
