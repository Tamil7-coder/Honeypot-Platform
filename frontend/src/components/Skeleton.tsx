export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-soc-panelBorder glass-panel px-5 py-4">
      <div className="skeleton h-3 w-24 rounded" />
      <div className="skeleton h-7 w-16 rounded mt-3" />
    </div>
  );
}

export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <tr className="border-b border-soc-panelBorder/50">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-2">
          <div className="skeleton h-3 w-full max-w-[120px] rounded" />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} />;
}
