import { useState, useRef, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, X, CheckCheck, Mail, MailWarning, MailQuestion } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import {
  fetchNotifications,
  markNotificationRead,
  dismissNotification,
  markAllNotificationsRead,
} from "../api/endpoints";
import SeverityBadge, { Severity } from "./SeverityBadge";

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => fetchNotifications(20),
    refetchInterval: 30_000,
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }

  async function handleMarkRead(id: string) {
    await markNotificationRead(id);
    invalidate();
  }

  async function handleDismiss(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await dismissNotification(id);
    invalidate();
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();
    invalidate();
  }

  const unreadCount = data?.unread_count ?? 0;
  const items = data?.items ?? [];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="relative rounded-lg p-2 text-soc-textMuted hover:bg-white/5 hover:text-slate-100 transition-colors"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-soc-danger px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-96 rounded-xl border border-soc-panelBorder glass-panel shadow-glass z-50"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-soc-panelBorder">
              <p className="text-sm font-semibold text-slate-200">
                Notifications {unreadCount > 0 && <span className="text-soc-danger">({unreadCount})</span>}
              </p>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1 text-[10px] text-soc-cyan hover:underline"
                >
                  <CheckCheck size={12} /> Mark all read
                </button>
              )}
            </div>

            {items.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-soc-textMuted">No notifications.</p>
                <p className="text-xs text-soc-textFaint mt-1">HIGH/CRITICAL attacks will appear here.</p>
              </div>
            ) : (
              <ul className="max-h-96 overflow-y-auto">
                {items.map((n) => (
                  <li
                    key={n.id}
                    onClick={() => !n.is_read && handleMarkRead(n.id)}
                    className={`px-4 py-3 border-b border-soc-panelBorder/50 last:border-0 cursor-pointer transition-colors ${
                      n.is_read ? "opacity-60 hover:opacity-100" : "bg-soc-cyan/5 hover:bg-soc-cyan/10"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 mb-1">
                        <SeverityBadge severity={n.severity.toUpperCase() as Severity} />
                        <span className="text-[10px] text-soc-textFaint">
                          {new Date(n.created_at).toLocaleString()}
                        </span>
                      </div>
                      <button
                        onClick={(e) => handleDismiss(n.id, e)}
                        className="text-soc-textFaint hover:text-soc-danger shrink-0"
                        title="Dismiss"
                      >
                        <X size={13} />
                      </button>
                    </div>
                    <p className="text-xs text-slate-300 mb-1.5">{n.message}</p>
                    <EmailStatus sent={n.email_sent} error={n.email_error} />
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EmailStatus({ sent, error }: { sent: boolean; error: string | null }) {
  if (sent) {
    return (
      <span className="flex items-center gap-1 text-[10px] text-soc-success">
        <Mail size={10} /> Email delivered
      </span>
    );
  }
  if (error === "SMTP not configured" || error === "ADMIN_ALERT_EMAIL not set") {
    return (
      <span className="flex items-center gap-1 text-[10px] text-soc-textFaint">
        <MailQuestion size={10} /> Email not configured
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[10px] text-soc-warning">
      <MailWarning size={10} /> Email failed{error ? `: ${error}` : ""}
    </span>
  );
}
