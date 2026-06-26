import { useEffect } from "react";

import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { useHealthStore } from "@/stores/health-store";

interface HealthResponse {
  status: string;
}

export function HealthPage() {
  const { status, data, error, setLoading, setOk, setError } = useHealthStore();

  const check = async () => {
    setLoading();
    try {
      const response = await apiGet<HealthResponse>("/health");
      setOk(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="mx-auto max-w-xl space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">后端健康检查</h2>
        <p className="text-sm text-muted-foreground">
          通过 <code className="rounded bg-muted px-1">GET /health</code> 探测后端存活状态。
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">状态</span>
          <StatusBadge status={status} />
        </div>
        {status === "ok" && data && (
          <pre className="rounded bg-muted p-3 text-xs">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
        {status === "error" && (
          <div className="rounded border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button onClick={() => void check()} disabled={status === "loading"}>
          {status === "loading" ? "检测中..." : "重新检测"}
        </Button>
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = {
    idle: "未启动",
    loading: "检测中",
    ok: "存活",
    error: "不可达",
  }[status] ?? status;
  const tone = {
    idle: "bg-muted text-muted-foreground",
    loading: "bg-accent text-accent-foreground",
    ok: "bg-primary text-primary-foreground",
    error: "bg-destructive text-destructive-foreground",
  }[status] ?? "bg-muted text-muted-foreground";
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${tone}`}>
      {label}
    </span>
  );
}
