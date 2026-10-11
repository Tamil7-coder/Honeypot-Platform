import { useState } from "react";
import { FileText, FileSpreadsheet, FileDown, Download, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { downloadReport, ReportFormat, ReportPeriod } from "../api/endpoints";
import Panel from "../components/Panel";

const PERIODS: { value: ReportPeriod; label: string; description: string }[] = [
  { value: "daily", label: "Daily", description: "Last 24 hours" },
  { value: "weekly", label: "Weekly", description: "Last 7 days" },
  { value: "monthly", label: "Monthly", description: "Last 30 days" },
];

const FORMATS: { value: ReportFormat; label: string; icon: typeof FileText; description: string }[] = [
  { value: "pdf", label: "PDF", icon: FileText, description: "Formatted document, ready to print or share" },
  { value: "xlsx", label: "Excel", icon: FileSpreadsheet, description: "Multi-sheet workbook for further analysis" },
  { value: "csv", label: "CSV", icon: FileDown, description: "Raw data for import into other tools" },
];

export default function ReportsPage() {
  const [period, setPeriod] = useState<ReportPeriod>("weekly");
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [status, setStatus] = useState<"idle" | "generating" | "done" | "error">("idle");

  async function handleGenerate() {
    setStatus("generating");
    try {
      await downloadReport(period, format);
      setStatus("done");
      setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 4000);
    }
  }

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Reports</h1>
        <p className="text-soc-textMuted text-sm">
          Generate a summary of attack activity — total attacks, severity breakdown, top
          attackers, credentials, and sessions — for the selected period.
        </p>
      </div>

      <Panel title="Report Period">
        <div className="grid grid-cols-3 gap-3">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                period === p.value
                  ? "border-soc-cyan bg-soc-cyan/10"
                  : "border-soc-panelBorder hover:border-soc-panelBorderHover"
              }`}
            >
              <p className={`text-sm font-semibold ${period === p.value ? "text-soc-cyan" : "text-slate-200"}`}>
                {p.label}
              </p>
              <p className="text-xs text-soc-textFaint mt-0.5">{p.description}</p>
            </button>
          ))}
        </div>
      </Panel>

      <Panel title="Export Format">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {FORMATS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFormat(f.value)}
              className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                format === f.value
                  ? "border-soc-cyan bg-soc-cyan/10"
                  : "border-soc-panelBorder hover:border-soc-panelBorderHover"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <f.icon size={15} className={format === f.value ? "text-soc-cyan" : "text-soc-textMuted"} />
                <p className={`text-sm font-semibold ${format === f.value ? "text-soc-cyan" : "text-slate-200"}`}>
                  {f.label}
                </p>
              </div>
              <p className="text-xs text-soc-textFaint">{f.description}</p>
            </button>
          ))}
        </div>
      </Panel>

      <div className="flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={status === "generating"}
          className="flex items-center gap-2 rounded-lg bg-signature-gradient px-5 py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {status === "generating" ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
          {status === "generating" ? "Generating..." : "Generate & Download"}
        </button>

        {status === "done" && (
          <span className="flex items-center gap-1.5 text-sm text-soc-success">
            <CheckCircle2 size={15} /> Downloaded
          </span>
        )}
        {status === "error" && (
          <span className="flex items-center gap-1.5 text-sm text-soc-danger">
            <AlertCircle size={15} /> Failed to generate report
          </span>
        )}
      </div>
    </div>
  );
}
