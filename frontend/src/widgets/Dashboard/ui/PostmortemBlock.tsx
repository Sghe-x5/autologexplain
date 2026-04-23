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
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <FileText className="h-4 w-4 text-slate-600" />
        <h2 className="text-sm font-semibold text-slate-900">
          Автоматический постмортем
        </h2>
        <span className="ml-auto rounded-md bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
          markdown
        </span>
      </div>

      {!data && !isFetching && (
        <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
          <FileText className="mx-auto h-6 w-6 text-slate-300" />
          <p className="mt-2 text-xs text-slate-500">
            Соберёт структурированный markdown-скелет на основе данных инцидента:
            summary, timing, RCA, evidence, timeline, похожие инциденты, action items.
          </p>
          <button
            onClick={handleGenerate}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-blue-700 hover:to-purple-700"
          >
            <FileText className="h-3 w-3" />
            Сгенерировать
          </button>
        </div>
      )}

      {isFetching && (
        <div className="py-6 text-center text-xs text-slate-400">
          Сборка постмортема…
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-50 p-3 text-xs text-red-700">
          Не удалось сгенерировать. Попробуй ещё раз.
        </div>
      )}

      {data && (
        <div>
          <div className="mb-2 flex justify-end gap-1.5">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-500" />
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
              className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-3 w-3" />
              .md
            </button>
            <button
              onClick={handleGenerate}
              className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50"
            >
              пересобрать
            </button>
          </div>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50 p-3 font-mono text-[11px] leading-relaxed text-slate-800">
            {data.markdown}
          </pre>
        </div>
      )}
    </div>
  );
};
