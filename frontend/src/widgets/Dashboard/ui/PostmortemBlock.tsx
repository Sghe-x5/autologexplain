import { useState } from "react";
import { FileText, Download, Copy, Check } from "lucide-react";
import { useLazyGetPostmortemQuery } from "@/api";

/**
 * Postmortem block — по кнопке вызывает API, отображает markdown с возможностью
 * скопировать и скачать.
 */
export const PostmortemBlock = ({ incidentId }: { incidentId: string }) => {
  const [fetchPostmortem, { data, isFetching, error }] =
    useLazyGetPostmortemQuery();
  const [copied, setCopied] = useState(false);

  const handleGenerate = () => {
    fetchPostmortem({ id: incidentId });
  };

  const handleCopy = async () => {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const handleDownload = () => {
    if (!data) return;
    const blob = new Blob([data.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `postmortem-${incidentId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-sky-500/10 ring-1 ring-sky-500/30">
          <FileText className="h-3.5 w-3.5 text-sky-400" />
        </div>
        <h2 className="text-sm font-semibold text-zinc-100">
          Автоматический постмортем
        </h2>
        <span className="ml-auto rounded-md border border-zinc-700 bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-400">
          markdown
        </span>
      </div>

      {!data && !isFetching && (
        <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950/40 p-6 text-center">
          <FileText className="mx-auto h-6 w-6 text-zinc-700" />
          <p className="mt-2 text-xs text-zinc-500">
            Соберёт структурированный markdown-скелет на основе данных инцидента:
            summary, timing, RCA, evidence, timeline, похожие инциденты, action items.
          </p>
          <button
            onClick={handleGenerate}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 px-3 py-1.5 text-xs font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:from-indigo-400 hover:to-violet-500"
          >
            <FileText className="h-3 w-3" />
            Сгенерировать
          </button>
        </div>
      )}

      {isFetching && (
        <div className="py-6 text-center font-mono text-xs text-zinc-500">
          <span className="text-violet-400">&gt;</span> Сборка постмортема…
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          Не удалось сгенерировать. Попробуй ещё раз.
        </div>
      )}

      {data && (
        <div>
          <div className="mb-2 flex justify-end gap-1.5">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-[11px] text-zinc-300 transition hover:border-violet-500/40 hover:text-violet-300"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  Скопировано
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  Copy
                </>
              )}
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-[11px] text-zinc-300 transition hover:border-violet-500/40 hover:text-violet-300"
            >
              <Download className="h-3 w-3" />
              .md
            </button>
            <button
              onClick={handleGenerate}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-[11px] text-zinc-300 transition hover:border-violet-500/40 hover:text-violet-300"
            >
              пересобрать
            </button>
          </div>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950/80 p-3 font-mono text-[11px] leading-relaxed text-zinc-300">
            {data.markdown}
          </pre>
        </div>
      )}
    </div>
  );
};
