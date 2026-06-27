import type { EtfPoolSummary } from "@/api/pools";

export interface PoolListProps {
  pools: EtfPoolSummary[];
  selectedId?: number | null;
  onSelect: (pool: EtfPoolSummary) => void;
  onDelete: (pool: EtfPoolSummary) => void;
  testId?: string;
}

export function PoolList({
  pools,
  selectedId = null,
  onSelect,
  onDelete,
  testId = "pool-list",
}: PoolListProps) {
  if (pools.length === 0) {
    return (
      <div
        className="rounded-lg border border-dashed bg-muted/30 p-8 text-center text-sm text-muted-foreground"
        data-testid={`${testId}-empty`}
      >
        暂无策略池，点击右上角"新建池"开始创建
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-1 gap-3 sm:grid-cols-2"
      data-testid={testId}
    >
      {pools.map((pool) => {
        const isSelected = pool.id === selectedId;
        return (
          <div
            key={pool.id}
            className={`group relative cursor-pointer rounded-lg border bg-card p-4 shadow-sm transition-all hover:border-primary hover:shadow ${
              isSelected ? "border-primary ring-1 ring-primary/30" : "border-border"
            }`}
            onClick={() => onSelect(pool)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(pool);
              }
            }}
            role="button"
            tabIndex={0}
            data-testid={`${testId}-card-${pool.id}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-base font-semibold">{pool.name}</h3>
                {pool.description && (
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {pool.description}
                  </p>
                )}
              </div>
              <span
                className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                data-testid={`${testId}-count-${pool.id}`}
              >
                {pool.member_count} 只
              </span>
            </div>

            <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(pool);
                }}
                className="rounded-md border border-rose-200 bg-white px-2 py-1 text-xs font-medium text-rose-600 shadow-sm hover:bg-rose-50"
                data-testid={`${testId}-delete-${pool.id}`}
                aria-label={`删除池 ${pool.name}`}
              >
                删除
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
