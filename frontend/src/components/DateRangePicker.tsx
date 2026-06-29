import { useEffect, useState } from "react";

export interface DateRange {
  from_date: string;
  to_date: string;
}

export interface DateRangePickerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (range: DateRange) => void;
  isSubmitting: boolean;
  errorMessage?: string | null;
}

function todayISO(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function DateRangePicker({
  open, onClose, onConfirm, isSubmitting, errorMessage,
}: DateRangePickerProps) {
  const [fromDate, setFromDate] = useState(todayISO(-30));
  const [toDate, setToDate] = useState(todayISO(0));

  useEffect(() => {
    if (open) {
      setFromDate(todayISO(-30));
      setToDate(todayISO(0));
    }
  }, [open]);

  if (!open) return null;

  const fromInvalid = fromDate > toDate;
  const canConfirm = !fromInvalid && !isSubmitting;

  return (
    <div role="dialog" aria-label="选择同步日期范围" className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded bg-background p-6 shadow-lg">
        <h3 className="mb-4 text-lg font-semibold">选择同步日期范围</h3>
        {errorMessage && (
          <p role="alert" className="mb-3 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}
        <div className="mb-4 space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block text-muted-foreground">From (开始日期)</span>
            <input
              type="date"
              value={fromDate}
              max={toDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full rounded border px-2 py-1"
              data-testid="from-date-input"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-muted-foreground">To (结束日期)</span>
            <input
              type="date"
              value={toDate}
              min={fromDate}
              max={todayISO(0)}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full rounded border px-2 py-1"
              data-testid="to-date-input"
            />
          </label>
          {fromInvalid && (
            <p role="alert" className="text-xs text-red-600">
              from_date 必须早于或等于 to_date
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
            data-testid="cancel-button"
          >
            取消
          </button>
          <button
            type="button"
            onClick={() => onConfirm({ from_date: fromDate, to_date: toDate })}
            disabled={!canConfirm}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
            data-testid="confirm-button"
          >
            {isSubmitting ? "同步中…" : "开始同步"}
          </button>
        </div>
      </div>
    </div>
  );
}