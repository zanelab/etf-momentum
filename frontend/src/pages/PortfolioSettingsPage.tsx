// Portfolio holdings configuration page — CRUD table for ETF positions.
import { useState } from "react";
import { usePortfolioHoldings, useUpsertHolding, useDeleteHolding } from "@/api/hooks";

interface HoldingRow {
  code: string;
  name: string;
  shares: number;
  cost_price: number;
}

interface EditState {
  code: string;
  name: string;
  shares: string;
  cost_price: string;
}

const EMPTY: EditState = { code: "", name: "", shares: "", cost_price: "" };

export default function PortfolioSettingsPage() {
  const { data: holdings = [], isLoading, error } = usePortfolioHoldings();
  const upsert = useUpsertHolding();
  const del = useDeleteHolding();

  const [editing, setEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditState>(EMPTY);
  const [addForm, setAddForm] = useState<EditState>(EMPTY);
  const [adding, setAdding] = useState(false);

  const startEdit = (h: HoldingRow) => {
    setEditing(h.code);
    setEditForm({ code: h.code, name: h.name, shares: String(h.shares), cost_price: String(h.cost_price) });
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditForm(EMPTY);
  };

  const submitEdit = async () => {
    await upsert.mutateAsync({
      code: editForm.code,
      name: editForm.name,
      shares: Number(editForm.shares),
      cost_price: Number(editForm.cost_price),
    });
    setEditing(null);
    setEditForm(EMPTY);
  };

  const submitAdd = async () => {
    await upsert.mutateAsync({
      code: addForm.code.trim().toUpperCase(),
      name: addForm.name.trim(),
      shares: Number(addForm.shares),
      cost_price: Number(addForm.cost_price),
    });
    setAddForm(EMPTY);
    setAdding(false);
  };

  if (isLoading) return <p className="text-muted-foreground text-sm">加载中…</p>;
  if (error) return <p className="text-red-600 text-sm">加载失败：{String(error)}</p>;

  const rows: HoldingRow[] = holdings;

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">持仓配置（{rows.length}）</h2>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            + 添加持仓
          </button>
        )}
      </header>

      {/* Add form */}
      {adding && (
        <div className="rounded border p-4 space-y-3 bg-muted/20">
          <p className="text-sm font-medium">添加新持仓</p>
          <div className="grid grid-cols-4 gap-3 text-sm">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">ETF 代码</label>
              <input
                className="w-full rounded border px-2 py-1 font-mono"
                placeholder="e.g. 510300"
                value={addForm.code}
                onChange={(e) => setAddForm({ ...addForm, code: e.target.value })}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">名称</label>
              <input
                className="w-full rounded border px-2 py-1"
                placeholder="e.g. 华泰柏瑞沪深300"
                value={addForm.name}
                onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">股数/份额</label>
              <input
                className="w-full rounded border px-2 py-1"
                type="number"
                min="0"
                placeholder="e.g. 1000"
                value={addForm.shares}
                onChange={(e) => setAddForm({ ...addForm, shares: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">成本价（元）</label>
              <input
                className="w-full rounded border px-2 py-1"
                type="number"
                min="0"
                step="0.001"
                placeholder="e.g. 3.850"
                value={addForm.cost_price}
                onChange={(e) => setAddForm({ ...addForm, cost_price: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={submitAdd}
              disabled={!addForm.code || !addForm.name || !addForm.shares || !addForm.cost_price}
              className="rounded bg-primary px-3 py-1 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40"
            >
              保存
            </button>
            <button
              onClick={() => { setAdding(false); setAddForm(EMPTY); }}
              className="rounded border px-3 py-1 text-sm hover:bg-muted"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {rows.length === 0 && !adding && (
        <div className="rounded border border-dashed p-8 text-center text-muted-foreground text-sm">
          暂无持仓。请点击右上角「添加持仓」添加你的 ETF 持仓。
        </div>
      )}

      {/* Holdings table */}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-3 py-2 text-left font-medium">ETF 代码</th>
                <th className="px-3 py-2 text-left font-medium">名称</th>
                <th className="px-3 py-2 text-right font-medium">持有份额</th>
                <th className="px-3 py-2 text-right font-medium">成本价（元）</th>
                <th className="px-3 py-2 text-right font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((h) => {
                const isEditing = editing === h.code;
                return (
                  <tr key={h.code} className="border-t">
                    {isEditing ? (
                      <>
                        <td className="px-3 py-1.5 font-mono">{h.code}</td>
                        <td className="px-3 py-1.5">
                          <input
                            className="w-full rounded border px-2 py-0.5"
                            value={editForm.name}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-1.5">
                          <input
                            className="w-full rounded border px-2 py-0.5 text-right"
                            type="number"
                            min="0"
                            value={editForm.shares}
                            onChange={(e) => setEditForm({ ...editForm, shares: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-1.5">
                          <input
                            className="w-full rounded border px-2 py-0.5 text-right"
                            type="number"
                            min="0"
                            step="0.001"
                            value={editForm.cost_price}
                            onChange={(e) => setEditForm({ ...editForm, cost_price: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-1.5 text-right">
                          <button
                            onClick={submitEdit}
                            className="mr-2 text-xs text-primary hover:underline"
                          >
                            保存
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="text-xs text-muted-foreground hover:underline"
                          >
                            取消
                          </button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-1.5 font-mono">{h.code}</td>
                        <td className="px-3 py-1.5">{h.name}</td>
                        <td className="px-3 py-1.5 text-right">{h.shares.toLocaleString()}</td>
                        <td className="px-3 py-1.5 text-right">¥{h.cost_price.toFixed(3)}</td>
                        <td className="px-3 py-1.5 text-right">
                          <button
                            onClick={() => startEdit(h)}
                            className="mr-3 text-xs text-muted-foreground hover:text-foreground"
                          >
                            编辑
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`删除持仓 ${h.code} ${h.name}？`)) {
                                del.mutate(h.code);
                              }
                            }}
                            className="text-xs text-red-600 hover:underline"
                          >
                            删除
                          </button>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {upsert.isError && (
        <p className="text-red-600 text-sm">保存失败：{(upsert.error as Error)?.message}</p>
      )}
      {del.isError && (
        <p className="text-red-600 text-sm">删除失败：{(del.error as Error)?.message}</p>
      )}
    </section>
  );
}