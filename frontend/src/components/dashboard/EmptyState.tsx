export function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed bg-muted/30 p-8 text-center">
      <h3 className="text-lg font-semibold">暂无信号快照</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        数据库中还没有计算过实时动量信号。请在 backend 目录运行：
      </p>
      <pre className="mx-auto mt-3 inline-block rounded bg-muted px-3 py-2 text-xs">
        python -m app.signals.compute_latest
      </pre>
    </div>
  );
}
