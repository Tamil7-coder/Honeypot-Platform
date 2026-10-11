import { useLiveFeed } from "../context/LiveFeedContext";

export default function LiveStatusIndicator() {
  const { isConnected } = useLiveFeed();

  return (
    <div
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide ring-1 ${
        isConnected
          ? "bg-soc-success/10 text-soc-success ring-soc-success/25"
          : "bg-soc-textFaint/10 text-soc-textFaint ring-soc-panelBorder"
      }`}
      title={isConnected ? "Live feed connected" : "Live feed disconnected — reconnecting..."}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-soc-success animate-pulse-slow" : "bg-soc-textFaint"}`} />
      {isConnected ? "Live" : "Offline"}
    </div>
  );
}
