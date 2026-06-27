import { useEffect, useState } from "react";

import { PoolEditor } from "@/components/pools/PoolEditor";
import { PoolList } from "@/components/pools/PoolList";
import type { EtfPoolSummary } from "@/api/pools";
import { useEtfsStore } from "@/stores/etfs-store";
import { usePoolsStore } from "@/stores/pools-store";

type EditTarget = { kind: "create" } | { kind: "edit"; pool: EtfPoolSummary };

export function PoolsPage() {
  const etfsState = useEtfsStore();
  const poolsState = usePoolsStore();

  const [target, setTarget] = useState<EditTarget | null>(null);

  useEffect(() => {
    void poolsState.fetchAll();
    if (etfsState.status === "idle") {
      void etfsState.fetchAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = (pool: EtfPoolSummary) => {
    poolsState.clearFormErrors();
    setTarget({ kind: "edit", pool });
    void poolsState.fetchOne(pool.id);
  };

  const handleDelete = (pool: EtfPoolSummary) => {
    const confirmed = window.confirm(`确认删除策略池「${pool.name}」？此操作不可撤销。`);
    if (!confirmed) return;
    void poolsState.remove(pool.id).then((ok) => {
      if (ok && target?.kind === "edit" && target.pool.id === pool.id) {
        setTarget(null);
      }
    });
  };

  const handleNew = () => {
    poolsState.clearFormErrors();
    setTarget({ kind: "create" });
  };

  const handleCancel = () => {
    poolsState.clearFormErrors();
    setTarget(null);
  };

  const handleSaveCreate = async (req: {
    name: string;
    description: string | null;
    etf_codes: string[];
  }) => {
    const detail = await poolsState.create(req);
    if (detail) {
      setTarget(null);
    }
  };

  const handleSaveEdit = async (req: {
    name: string;
    description: string | null;
    etf_codes: string[];
  }) => {
    if (target?.kind !== "edit") return;
    const detail = await poolsState.update(target.pool.id, req);
    if (detail) {
      setTarget(null);
    }
  };

  const etfs = etfsState.data?.items ?? [];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">策略池</h2>
          <p className="text-sm text-muted-foreground">
            管理用户自定义的 ETF 策略池，可在回测时一键复用
          </p>
        </div>
        <button
          type="button"
          onClick={handleNew}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
          data-testid="pools-new"
        >
          新建池
        </button>
      </div>

      {poolsState.status === "loading" && (
        <div className="rounded-lg border bg-card p-6 text-sm text-muted-foreground shadow-sm" data-testid="pools-loading">
          加载中…
        </div>
      )}

      {poolsState.status === "error" && (
        <div
          className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 shadow-sm"
          data-testid="pools-error"
        >
          <div className="font-medium">加载策略池失败</div>
          <div className="mt-1">{poolsState.error}</div>
          <button
            type="button"
            onClick={() => void poolsState.fetchAll()}
            className="mt-3 rounded-md border bg-white px-3 py-1 text-xs font-medium text-rose-700 shadow-sm hover:bg-rose-100"
            data-testid="pools-retry"
          >
            重试
          </button>
        </div>
      )}

      {poolsState.status === "ok" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.4fr]">
          <div data-testid="pools-list-wrapper">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              我的策略池（{poolsState.items.length}）
            </h3>
            <PoolList
              pools={poolsState.items}
              selectedId={target?.kind === "edit" ? target.pool.id : null}
              onSelect={handleSelect}
              onDelete={handleDelete}
            />
          </div>

          <div data-testid="pools-editor-wrapper">
            {target === null && (
              <div
                className="flex h-full min-h-[200px] items-center justify-center rounded-lg border border-dashed bg-muted/30 p-8 text-center text-sm text-muted-foreground"
                data-testid="pools-editor-empty"
              >
                从左侧选择一个池进行编辑，或点击右上角"新建池"
              </div>
            )}

            {target?.kind === "create" && (
              <PoolEditor
                key="new"
                mode="create"
                etfs={etfs}
                etfsLoading={etfsState.status === "loading" || etfsState.status === "idle"}
                etfsError={etfsState.status === "error" ? etfsState.error : null}
                submitStatus={poolsState.createStatus}
                submitError={poolsState.createError}
                formErrors={poolsState.formErrors}
                onSave={handleSaveCreate}
                onCancel={handleCancel}
              />
            )}

            {target?.kind === "edit" && (
              <>
                {poolsState.currentPool?.id === target.pool.id ? (
                  <PoolEditor
                    key={target.pool.id}
                    mode="edit"
                    initialName={poolsState.currentPool.name}
                    initialDescription={poolsState.currentPool.description}
                    initialCodes={poolsState.currentPool.members.map((m) => m.code)}
                    etfs={etfs}
                    etfsLoading={etfsState.status === "loading" || etfsState.status === "idle"}
                    etfsError={etfsState.status === "error" ? etfsState.error : null}
                    submitStatus={poolsState.updateStatus}
                    submitError={poolsState.updateError}
                    formErrors={poolsState.formErrors}
                    onSave={handleSaveEdit}
                    onCancel={handleCancel}
                  />
                ) : (
                  <div
                    className="flex items-center gap-3 rounded-lg border bg-card p-6 text-sm text-muted-foreground shadow-sm"
                    data-testid="pools-editor-loading"
                  >
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-primary" />
                    加载池详情…
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
