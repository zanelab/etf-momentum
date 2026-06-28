// Theme keyword dictionary editor.
import { useState } from "react";

import { useReplaceThemes, useThemes } from "@/api/hooks";

export default function ThemeConfig() {
  const themes = useThemes();
  const replace = useReplaceThemes();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);

  if (themes.isLoading) return <p>加载中…</p>;
  if (themes.error) return <p className="text-red-600">加载失败</p>;

  const current: Record<string, string[]> = themes.data?.themes ?? {};
  const keywordText = (theme: string) =>
    dirty && draft[theme] !== undefined ? draft[theme] : (current[theme] ?? []).join(", ");

  const save = () => {
    const next: Record<string, string[]> = {};
    for (const t of Object.keys(current)) {
      next[t] = (dirty ? draft[t] : current[t].join(", "))
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    replace.mutate(next, {
      onSuccess: () => {
        setDirty(false);
        setDraft({});
      },
    });
  };

  return (
    <section>
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">主题词典</h2>
        <div className="flex gap-2">
          <button
            className="rounded border px-3 py-1 text-sm"
            disabled={!dirty || replace.isPending}
            onClick={() => {
              setDirty(false);
              setDraft({});
            }}
          >
            取消
          </button>
          <button
            className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
            disabled={!dirty || replace.isPending}
            onClick={save}
          >
            保存
          </button>
        </div>
      </header>
      <div className="grid gap-3">
        {Object.entries(current).map(([theme, kws]) => (
          <label key={theme} className="grid grid-cols-[120px_1fr] items-center gap-3">
            <span className="font-medium">{theme}</span>
            <input
              className="rounded border px-2 py-1 text-sm"
              value={keywordText(theme)}
              onChange={(e) => {
                setDirty(true);
                setDraft((d) => ({ ...d, [theme]: e.target.value }));
              }}
            />
            <span className="col-start-2 text-xs text-muted-foreground">
              关键词：{kws.join("、")}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}
