import React, { useState, useEffect, useCallback } from "react";
import "./Announcements.css";
import Sidebar from "./Sidebar";

const API = "/api";

function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TYPE_META = {
  announcement: { label: "Announcement", emoji: "📢" },
  reminder: { label: "Reminder", emoji: "⏰" },
};

const AUDIENCE_LABEL = {
  all: "All members",
  admins: "Admins / staff only",
  members: "Members only",
};

// ─── Admin: compose + send a new announcement (SCRUM-62 / SCRUM-63) ────────────

function ComposeForm({ onSent }) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [msgType, setMsgType] = useState("announcement");
  const [audience, setAudience] = useState("all");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    if (!title.trim() || !body.trim()) {
      setError("Title and message are both required.");
      return;
    }
    setSending(true);
    try {
      const res = await fetch(`${API}/announcements/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ title, body, msg_type: msgType, audience }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Could not send the message.");
        return;
      }
      setTitle("");
      setBody("");
      onSent(data);
    } catch (e) {
      setError("Network error. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="ann-compose">
      <h2 className="ann-compose__title">New message</h2>

      <div className="ann-field-row">
        <label className="ann-field">
          <span>Type</span>
          <select
            className="ann-select"
            value={msgType}
            onChange={(e) => setMsgType(e.target.value)}
          >
            <option value="announcement">📢 Announcement</option>
            <option value="reminder">⏰ Reminder</option>
          </select>
        </label>

        <label className="ann-field">
          <span>Send to</span>
          <select
            className="ann-select"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          >
            <option value="all">All members</option>
            <option value="members">Members only (non-admin)</option>
            <option value="admins">Admins / staff only</option>
          </select>
        </label>
      </div>

      <label className="ann-field">
        <span>Title</span>
        <input
          className="ann-input"
          placeholder="e.g. New ballot opens Monday"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={255}
        />
      </label>

      <label className="ann-field">
        <span>Message</span>
        <textarea
          className="ann-textarea"
          rows={4}
          placeholder="Write the announcement or reminder members will receive…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </label>

      {error && <div className="ann-error">{error}</div>}

      <button className="ann-btn ann-btn--primary" onClick={submit} disabled={sending}>
        {sending ? "Sending…" : "Send to members"}
      </button>
    </div>
  );
}

// ─── Admin: history of sent messages ──────────────────────────────────────────

function SentList({ items }) {
  if (!items.length) {
    return <p className="ann-empty">No messages sent yet. Compose one above to get started.</p>;
  }
  return (
    <div className="ann-list">
      {items.map((a) => {
        const meta = TYPE_META[a.msg_type] || TYPE_META.announcement;
        return (
          <div key={a.id} className="ann-card">
            <div className="ann-card__head">
              <span className="ann-card__type">{meta.emoji} {meta.label}</span>
              <span className="ann-card__date">{formatDateTime(a.created_at)}</span>
            </div>
            <h3 className="ann-card__title">{a.title}</h3>
            <p className="ann-card__body">{a.body}</p>
            <div className="ann-card__foot">
              <span className="ann-pill">{AUDIENCE_LABEL[a.audience] || a.audience}</span>
              <span className="ann-pill ann-pill--muted">
                Delivered to {a.recipient_count} member{a.recipient_count === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Member: inbox of received messages (SCRUM-63 recipient side) ─────────────

function Inbox({ items, onMarkRead }) {
  if (!items.length) {
    return <p className="ann-empty">Your inbox is empty. Announcements from admins will show up here.</p>;
  }
  return (
    <div className="ann-list">
      {items.map((m) => {
        const meta = TYPE_META[m.msg_type] || TYPE_META.announcement;
        return (
          <div
            key={m.id}
            className={`ann-card ann-card--inbox ${m.is_read ? "" : "ann-card--unread"}`}
          >
            <div className="ann-card__head">
              <span className="ann-card__type">{meta.emoji} {meta.label}</span>
              <span className="ann-card__date">{formatDateTime(m.created_at)}</span>
            </div>
            <h3 className="ann-card__title">
              {!m.is_read && <span className="ann-dot" aria-label="Unread" />}
              {m.title}
            </h3>
            <p className="ann-card__body">{m.body}</p>
            {!m.is_read && (
              <button className="ann-btn ann-btn--ghost" onClick={() => onMarkRead(m.id)}>
                Mark as read
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Announcements({ user, onLogout, onNavigate }) {
  const isAdmin = !!user.is_admin;
  const [sent, setSent] = useState([]);
  const [inbox, setInbox] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(isAdmin ? "compose" : "inbox");

  const loadSent = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${API}/announcements/`, { credentials: "include" });
      if (res.ok) setSent(await res.json());
    } catch (e) { /* ignore */ }
  }, [isAdmin]);

  const loadInbox = useCallback(async () => {
    try {
      const res = await fetch(`${API}/inbox/`, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setInbox(data.items || []);
      }
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    Promise.all([loadSent(), loadInbox()]).finally(() => setLoading(false));
  }, [loadSent, loadInbox]);

  const handleSent = () => {
    loadSent();
    loadInbox();
  };

  const markRead = async (id) => {
    try {
      const res = await fetch(`${API}/inbox/${id}/read/`, {
        method: "POST",
        credentials: "include",
      });
      if (res.ok) {
        setInbox((prev) =>
          prev.map((m) => (m.id === id ? { ...m, is_read: true } : m))
        );
      }
    } catch (e) { /* ignore */ }
  };

  const unread = inbox.filter((m) => !m.is_read).length;

  return (
    <div className="ann-layout">
      <Sidebar user={user} active="announcements" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="ann-main">
        <header className="ann-header">
          <div>
            <h1>Announcements &amp; Reminders</h1>
            <p className="ann-header__sub">
              {isAdmin
                ? "Send platform-wide messages and reminders to your members."
                : "Messages and reminders sent to you by the team."}
            </p>
          </div>
        </header>

        {isAdmin && (
          <div className="ann-tabs">
            <button
              className={`ann-tab ${tab === "compose" ? "active" : ""}`}
              onClick={() => setTab("compose")}
            >
              Compose
            </button>
            <button
              className={`ann-tab ${tab === "sent" ? "active" : ""}`}
              onClick={() => setTab("sent")}
            >
              Sent ({sent.length})
            </button>
            <button
              className={`ann-tab ${tab === "inbox" ? "active" : ""}`}
              onClick={() => setTab("inbox")}
            >
              My inbox{unread > 0 ? ` (${unread})` : ""}
            </button>
          </div>
        )}

        {loading ? (
          <p className="ann-empty">Loading…</p>
        ) : (
          <>
            {isAdmin && tab === "compose" && <ComposeForm onSent={handleSent} />}
            {isAdmin && tab === "sent" && <SentList items={sent} />}
            {(tab === "inbox" || !isAdmin) && (
              <Inbox items={inbox} onMarkRead={markRead} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
