import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { X, ShieldQuestion, Globe, Building2, Network, MapPin, ExternalLink } from "lucide-react";
import { fetchIpReputation } from "../api/endpoints";
import SeverityBadge, { Severity } from "./SeverityBadge";
import { SkeletonBlock } from "./Skeleton";

const ERROR_LABELS: Record<string, string> = {
  not_configured: "Not configured — add an API key in .env",
  timeout: "Request timed out",
  unavailable: "No data available",
  "private range": "Private/internal IP — no public location data",
  "reserved range": "Reserved IP range — no public location data",
  "invalid query": "Invalid IP address",
};

function errorLabel(error: string | null): string {
  if (!error) return "";
  return ERROR_LABELS[error] ?? `Lookup failed (${error})`;
}

export default function ThreatIntelPanel({ ip, onClose }: { ip: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["threat-intel", ip],
    queryFn: () => fetchIpReputation(ip),
  });

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/60"
        onClick={onClose}
      />
      <motion.div
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-soc-panelBorder glass-panel p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wide">Threat Intelligence</h2>
            <p className="text-xs text-soc-textFaint font-mono mt-0.5">{ip}</p>
          </div>
          <button onClick={onClose} className="text-soc-textMuted hover:text-slate-100">
            <X size={18} />
          </button>
        </div>

        {isLoading && (
          <div className="space-y-3">
            <SkeletonBlock className="h-10" />
            <SkeletonBlock className="h-24" />
            <SkeletonBlock className="h-24" />
            <SkeletonBlock className="h-24" />
          </div>
        )}

        {error && <p className="text-sm text-soc-danger">Failed to load threat intelligence.</p>}

        {data && (
          <div className="space-y-5">
            <div className="flex items-center justify-between rounded-lg border border-soc-panelBorder bg-white/5 px-4 py-3">
              <span className="text-xs text-soc-textMuted uppercase">Overall Threat Level</span>
              {data.threat_level ? (
                <SeverityBadge severity={data.threat_level.toUpperCase() as Severity} />
              ) : (
                <span className="text-xs text-soc-textFaint flex items-center gap-1">
                  <ShieldQuestion size={13} /> Insufficient data
                </span>
              )}
            </div>

            <ProviderSection title="Geolocation" icon={MapPin} result={data.geolocation}>
              {data.geolocation.data && (
                <>
                  <dl className="text-xs space-y-1.5 mb-3">
                    <Row
                      label="City"
                      value={`${data.geolocation.data.city ?? "—"}${
                        data.geolocation.data.zip_code ? ` (${data.geolocation.data.zip_code})` : ""
                      }`}
                    />
                    <Row label="Region" value={String(data.geolocation.data.region ?? "—")} />
                    <Row
                      label="Country"
                      value={`${data.geolocation.data.country ?? "—"}${
                        data.geolocation.data.country_code ? ` (${data.geolocation.data.country_code})` : ""
                      }`}
                    />
                    <Row label="ISP" value={String(data.geolocation.data.isp ?? "—")} />
                    <Row label="Organization" value={String(data.geolocation.data.org ?? "—")} />
                    <Row label="Timezone" value={String(data.geolocation.data.timezone ?? "—")} />
                  </dl>

                  {typeof data.geolocation.data.latitude === "number" &&
                    typeof data.geolocation.data.longitude === "number" && (
                      <GeoMap lat={data.geolocation.data.latitude} lon={data.geolocation.data.longitude} />
                    )}
                </>
              )}
            </ProviderSection>

            <ProviderSection title="AbuseIPDB" icon={ShieldQuestion} result={data.abuseipdb}>
              {data.abuseipdb.data && (
                <dl className="text-xs space-y-1.5">
                  <Row label="Abuse Confidence" value={`${data.abuseipdb.data.abuse_confidence_score}%`} />
                  <Row label="Total Reports" value={String(data.abuseipdb.data.total_reports)} />
                  <Row label="Whitelisted" value={data.abuseipdb.data.is_whitelisted ? "Yes" : "No"} />
                  <Row label="ISP" value={String(data.abuseipdb.data.isp ?? "—")} />
                  <Row label="Country" value={String(data.abuseipdb.data.country_code ?? "—")} />
                </dl>
              )}
            </ProviderSection>

            <ProviderSection title="VirusTotal" icon={Network} result={data.virustotal}>
              {data.virustotal.data && (
                <dl className="text-xs space-y-1.5">
                  <Row label="Malicious Detections" value={String(data.virustotal.data.malicious)} />
                  <Row label="Suspicious" value={String(data.virustotal.data.suspicious)} />
                  <Row label="ASN" value={String(data.virustotal.data.asn ?? "—")} />
                  <Row label="AS Owner" value={String(data.virustotal.data.as_owner ?? "—")} />
                  <Row label="Country" value={String(data.virustotal.data.country ?? "—")} />
                </dl>
              )}
            </ProviderSection>

            <ProviderSection title="AlienVault OTX" icon={Globe} result={data.otx}>
              {data.otx.data && (
                <dl className="text-xs space-y-1.5">
                  <Row label="Pulse Count" value={String(data.otx.data.pulse_count)} />
                  <Row label="Reputation" value={String(data.otx.data.reputation ?? "—")} />
                  <Row label="Country" value={String(data.otx.data.country_name ?? "—")} />
                  <Row label="ASN" value={String(data.otx.data.asn ?? "—")} />
                </dl>
              )}
            </ProviderSection>

            <p className="text-[10px] text-soc-textFaint flex items-center gap-1.5">
              <Building2 size={11} />
              {data.from_cache ? "Served from cache" : "Freshly fetched"} · {new Date(data.fetched_at).toLocaleString()}
            </p>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

function ProviderSection({
  title,
  icon: Icon,
  result,
  children,
}: {
  title: string;
  icon: typeof Globe;
  result: { data: Record<string, unknown> | null; error: string | null };
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-soc-panelBorder bg-white/5 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className="text-soc-cyan" />
        <span className="text-xs font-semibold text-slate-200">{title}</span>
      </div>
      {result.data ? children : <p className="text-xs text-soc-textFaint">{errorLabel(result.error)}</p>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-soc-textMuted">{label}</dt>
      <dd className="text-slate-200 font-mono">{value}</dd>
    </div>
  );
}

function GeoMap({ lat, lon }: { lat: number; lon: number }) {
  // Small bounding box around the point for the embed's zoom level.
  const delta = 0.15;
  const bbox = `${lon - delta},${lat - delta},${lon + delta},${lat + delta}`;
  const embedSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lon}`;
  const fullMapUrl = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=11/${lat}/${lon}`;

  return (
    <div className="rounded-lg overflow-hidden border border-soc-panelBorder">
      <iframe
        title="Attacker location"
        src={embedSrc}
        className="w-full h-40 grayscale-[30%] opacity-90"
        loading="lazy"
      />
      <a
        href={fullMapUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-1.5 bg-black/30 py-1.5 text-[10px] text-soc-cyan hover:underline"
      >
        <ExternalLink size={10} /> Open full map
      </a>
    </div>
  );
}
