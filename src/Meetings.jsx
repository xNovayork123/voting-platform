import React, { useState, useEffect, useCallback } from "react";
import "./Meetings.css";
import Sidebar from "./Sidebar";

const API = "/api";

// ─── Tiny helpers ──────────────────────────────────────────────────────────────

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

const STATUS_LABELS = {
  scheduled: { label: "Scheduled", emoji: "🗓️" },
  in_progress: { label: "In Progress", emoji: "🟢" },
  done: { label: "Done", emoji: "✅" },
  cancelled: { label: "Cancelled", emoji: "❌" },
};

// ─── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const s = STATUS_LABELS[status] || { label: status, emoji: "•" };
  return (
    <span className={`meeting-badge meeting-badge--${status}`}>
      {s.emoji} {s.label}
    </span>
  );
}

// ─── Participant row inside the form ──────────────────────────────────────────

function ParticipantRow({ participant, index, onChange, onRemove }) {
  const handle = (field) => (e) =>
    onChange(index, { ...participant, [field]: e.target.value });

  return (
    <div className="participant-row">
      <input
        className="meetings-input"
        placeholder="Full name *"
        value={participant.name}
        onChange={handle("name")}
        required
      />
      <input
        className="meetings-input"
        type="email"
        placeholder="Email"
        value={participant.email}
        onChange={handle("email")}
      />
      <input
        className="meetings-input"
        placeholder="Phone (+49…)"
        value={participant.phone}
        onChange={handle("phone")}
      />
      <select
        className="meetings-select"
        value={participant.notification_channel}
        onChange={handle("notification_channel")}
      >
        <option value="email">Email only</option>
        <option value="whatsapp">WhatsApp only</option>
        <option value="both">Email + WhatsApp</option>
      </select>
      <button
        type="button"
        className="meetings-btn meetings-btn--ghost meetings-btn--sm"
        onClick={() => onRemove(index)}
        title="Remove participant"
      >
        ✕
      </button>
    </div>
  );
}

// ─── Schedule / Edit modal ─────────────────────────────────────────────────────

function MeetingFormModal({ meeting, onSave, onClose }) {
  const isEdit = Boolean(meeting?.id);

  const [form, setForm] = useState({
    title: meeting?.title || "",
    description: meeting?.description || "",
    location: meeting?.location || "",
    scheduled_at: meeting?.scheduled_at
      ? new Date(meeting.scheduled_at).toISOString().slice(0, 16)
      : "",
    duration_minutes: meeting?.duration_minutes || 60,
    status: meeting?.status || "scheduled",
    participants: meeting?.participants || [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const addParticipant = () =>
    setForm((f) => ({
      ...f,
      participants: [
        ...f.participants,
        { name: "", email: "", phone: "", notification_channel: "email" },
      ],
    }));

  const updateParticipant = (i, updated) =>
    setForm((f) => {
      const parts = [...f.participants];
      parts[i] = updated;
      return { ...f, participants: parts };
    });

  const removeParticipant = (i) =>
    setForm((f) => ({
      ...f,
      participants: f.participants.filter((_, idx) => idx !== i),
    }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    const body = {
      ...form,
      // Convert local datetime string back to ISO for Django
      scheduled_at: new Date(form.scheduled_at).toISOString(),
      duration_minutes: Number(form.duration_minutes),
    };

    try {
      const url = isEdit ? `${API}/meetings/${meeting.id}/` : `${API}/meetings/`;
      const method = isEdit ? "PATCH" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      onSave(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="meetings-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="meetings-modal">
        <header className="meetings-modal__header">
          <h2>{isEdit ? "Edit Meeting" : "Schedule a Meeting"}</h2>
          <button className="meetings-modal__close" onClick={onClose}>✕</button>
        </header>

        <form onSubmit={handleSubmit} className="meetings-form">
          {/* Basic info */}
          <section className="meetings-form__section">
            <h3>Meeting Details</h3>
            <label className="meetings-label">
              Title *
              <input
                className="meetings-input"
                value={form.title}
                onChange={set("title")}
                required
                placeholder="e.g. Q3 Planning Session"
              />
            </label>
            <label className="meetings-label">
              Description
              <textarea
                className="meetings-input meetings-textarea"
                value={form.description}
                onChange={set("description")}
                placeholder="Agenda, goals, or any notes…"
                rows={3}
              />
            </label>
            <div className="meetings-row">
              <label className="meetings-label">
                Date & Time *
                <input
                  className="meetings-input"
                  type="datetime-local"
                  value={form.scheduled_at}
                  onChange={set("scheduled_at")}
                  required
                />
              </label>
              <label className="meetings-label">
                Duration (minutes)
                <input
                  className="meetings-input"
                  type="number"
                  min={5}
                  max={480}
                  value={form.duration_minutes}
                  onChange={set("duration_minutes")}
                />
              </label>
            </div>
            <label className="meetings-label">
              Location / Link
              <input
                className="meetings-input"
                value={form.location}
                onChange={set("location")}
                placeholder="Conference Room A, or https://meet.example.com/xyz"
              />
            </label>
            {isEdit && (
              <label className="meetings-label">
                Status
                <select
                  className="meetings-select"
                  value={form.status}
                  onChange={set("status")}
                >
                  <option value="scheduled">Scheduled</option>
                  <option value="in_progress">In Progress</option>
                  <option value="done">Done</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
            )}
          </section>

          {/* Participants */}
          <section className="meetings-form__section">
            <div className="meetings-form__section-header">
              <h3>Participants</h3>
              <button
                type="button"
                className="meetings-btn meetings-btn--ghost meetings-btn--sm"
                onClick={addParticipant}
              >
                + Add Person
              </button>
            </div>
            {form.participants.length === 0 && (
              <p className="meetings-empty-hint">
                No participants yet. Click "+ Add Person" to invite someone.
              </p>
            )}
            {form.participants.map((p, i) => (
              <ParticipantRow
                key={i}
                index={i}
                participant={p}
                onChange={updateParticipant}
                onRemove={removeParticipant}
              />
            ))}
          </section>

          {error && <p className="meetings-error">{error}</p>}

          <footer className="meetings-modal__footer">
            <button
              type="button"
              className="meetings-btn meetings-btn--ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="meetings-btn meetings-btn--primary"
              disabled={saving}
            >
              {saving ? "Saving…" : isEdit ? "Save Changes" : "Schedule Meeting"}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}

// ─── Archive upload modal ──────────────────────────────────────────────────────

function ArchiveModal({ meeting, onSaved, onClose }) {
  const [archiveType, setArchiveType] = useState("transcript");
  const [videoFile, setVideoFile] = useState(null);
  const [transcriptFile, setTranscriptFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    const formData = new FormData();
    formData.append("archive_type", archiveType);
    formData.append("notes", notes);
    if (videoFile) formData.append("video_file", videoFile);
    if (transcriptFile) formData.append("transcript_file", transcriptFile);

    try {
      const res = await fetch(`${API}/meetings/${meeting.id}/archive/`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      onSaved();
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="meetings-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="meetings-modal">
        <header className="meetings-modal__header">
          <h2>Archive Meeting</h2>
          <button className="meetings-modal__close" onClick={onClose}>✕</button>
        </header>

        <form onSubmit={handleSubmit} className="meetings-form">
          <section className="meetings-form__section">
            <p className="meetings-modal__subtitle">
              Archiving: <strong>{meeting.title}</strong>
            </p>

            <label className="meetings-label">
              Archive type
              <select
                className="meetings-select"
                value={archiveType}
                onChange={(e) => setArchiveType(e.target.value)}
              >
                <option value="video">Video recording only</option>
                <option value="transcript">Transcript only</option>
                <option value="both">Video + Transcript</option>
              </select>
            </label>

            {(archiveType === "video" || archiveType === "both") && (
              <label className="meetings-label">
                Video file
                <input
                  className="meetings-input"
                  type="file"
                  accept="video/*"
                  onChange={(e) => setVideoFile(e.target.files[0])}
                />
              </label>
            )}

            {(archiveType === "transcript" || archiveType === "both") && (
              <label className="meetings-label">
                Transcript file (PDF, DOCX, TXT)
                <input
                  className="meetings-input"
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setTranscriptFile(e.target.files[0])}
                />
              </label>
            )}

            <label className="meetings-label">
              Meeting minutes / notes
              <textarea
                className="meetings-input meetings-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Decisions made, action items, attendees…"
                rows={5}
              />
            </label>
          </section>

          {error && <p className="meetings-error">{error}</p>}

          <footer className="meetings-modal__footer">
            <button
              type="button"
              className="meetings-btn meetings-btn--ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="meetings-btn meetings-btn--primary"
              disabled={saving}
            >
              {saving ? "Uploading…" : "Save Archive"}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}

// ─── Meeting card ──────────────────────────────────────────────────────────────

function MeetingCard({ meeting, isAdmin, onEdit, onArchive, onNotify, onDelete }) {
  const [notifying, setNotifying] = useState(false);
  const [notifyResult, setNotifyResult] = useState(null);

  const handleNotify = async () => {
    setNotifying(true);
    setNotifyResult(null);
    try {
      const res = await fetch(`${API}/meetings/${meeting.id}/notify/`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      const total = data.results?.length || 0;
      const ok = data.results?.filter((r) => r.success).length || 0;
      setNotifyResult(`✅ Sent to ${ok}/${total} participants`);
    } catch {
      setNotifyResult("❌ Notification failed");
    } finally {
      setNotifying(false);
      onNotify();
    }
  };

  return (
    <div className={`meeting-card meeting-card--${meeting.status}`}>
      <div className="meeting-card__top">
        <div>
          <h3 className="meeting-card__title">{meeting.title}</h3>
          {meeting.description && (
            <p className="meeting-card__desc">{meeting.description}</p>
          )}
        </div>
        <StatusBadge status={meeting.status} />
      </div>

      <div className="meeting-card__meta">
        <span>🗓 {formatDateTime(meeting.scheduled_at)}</span>
        <span>⏱ {meeting.duration_minutes} min</span>
        {meeting.location && <span>📍 {meeting.location}</span>}
        <span>👥 {meeting.participant_count} participant{meeting.participant_count !== 1 ? "s" : ""}</span>
        {meeting.has_archive && <span className="meeting-card__archived">📦 Archived</span>}
      </div>

      {notifyResult && (
        <p className="meeting-card__notify-result">{notifyResult}</p>
      )}

      {isAdmin && (
        <div className="meeting-card__actions">
          <button
            className="meetings-btn meetings-btn--ghost meetings-btn--sm"
            onClick={() => onEdit(meeting)}
          >
            ✏️ Edit
          </button>
          {meeting.status !== "done" && meeting.status !== "cancelled" && (
            <button
              className="meetings-btn meetings-btn--ghost meetings-btn--sm"
              onClick={handleNotify}
              disabled={notifying}
            >
              {notifying ? "Sending…" : "📨 Notify"}
            </button>
          )}
          {meeting.status === "done" && !meeting.has_archive && (
            <button
              className="meetings-btn meetings-btn--ghost meetings-btn--sm"
              onClick={() => onArchive(meeting)}
            >
              📦 Archive
            </button>
          )}
          <button
            className="meetings-btn meetings-btn--danger meetings-btn--sm"
            onClick={() => onDelete(meeting)}
          >
            🗑 Delete
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Meetings page ────────────────────────────────────────────────────────

export default function Meetings({ user, onLogout, onNavigate }) {
  const isAdmin = user?.is_staff || user?.is_admin;

  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const [modal, setModal] = useState(null); // null | "create" | "edit" | "archive"
  const [selectedMeeting, setSelectedMeeting] = useState(null);

  const fetchMeetings = useCallback(() => {
    setLoading(true);
    fetch(`${API}/meetings/`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setMeetings(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  const handleDelete = async (meeting) => {
    if (!window.confirm(`Delete "${meeting.title}"? This cannot be undone.`)) return;
    await fetch(`${API}/meetings/${meeting.id}/`, {
      method: "DELETE",
      credentials: "include",
    });
    fetchMeetings();
  };

  const openEdit = (meeting) => {
    setSelectedMeeting(meeting);
    setModal("edit");
  };

  const openArchive = (meeting) => {
    setSelectedMeeting(meeting);
    setModal("archive");
  };

  const closeModal = () => {
    setModal(null);
    setSelectedMeeting(null);
  };

  const onSaved = () => {
    closeModal();
    fetchMeetings();
  };

  const filtered =
    filter === "all" ? meetings : meetings.filter((m) => m.status === filter);

  const counts = meetings.reduce(
    (acc, m) => ({ ...acc, [m.status]: (acc[m.status] || 0) + 1 }),
    {}
  );

  return (
    <div className="meetings-layout">
      <Sidebar user={user} active="meetings" onLogout={onLogout} onNavigate={onNavigate} />

      {/* ── Main content ── */}
      <main className="meetings-main">
        <header className="meetings-header">
          <div>
            <h1>Meetings</h1>
            <p className="meetings-header__sub">
              Schedule, notify participants, and archive completed sessions.
            </p>
          </div>
          {isAdmin && (
            <button
              className="meetings-btn meetings-btn--primary"
              onClick={() => setModal("create")}
            >
              + Schedule Meeting
            </button>
          )}
        </header>

        {/* Stats row */}
        <div className="meetings-stats">
          {Object.entries(STATUS_LABELS).map(([key, { label, emoji }]) => (
            <div key={key} className="meetings-stat">
              <span className="meetings-stat__emoji">{emoji}</span>
              <span className="meetings-stat__value">{counts[key] || 0}</span>
              <span className="meetings-stat__label">{label}</span>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div className="meetings-filters">
          {["all", "scheduled", "in_progress", "done", "cancelled"].map((f) => (
            <button
              key={f}
              className={`meetings-filter-btn ${filter === f ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : STATUS_LABELS[f]?.label}
            </button>
          ))}
        </div>

        {/* Meeting cards */}
        {loading ? (
          <div className="meetings-loading">Loading meetings…</div>
        ) : filtered.length === 0 ? (
          <div className="meetings-empty">
            <span>📅</span>
            <p>No {filter !== "all" ? filter : ""} meetings found.</p>
            {isAdmin && (
              <button
                className="meetings-btn meetings-btn--primary"
                onClick={() => setModal("create")}
              >
                Schedule the first one
              </button>
            )}
          </div>
        ) : (
          <div className="meetings-list">
            {filtered.map((m) => (
              <MeetingCard
                key={m.id}
                meeting={m}
                isAdmin={isAdmin}
                onEdit={openEdit}
                onArchive={openArchive}
                onNotify={fetchMeetings}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      {/* ── Modals ── */}
      {modal === "create" && (
        <MeetingFormModal meeting={null} onSave={onSaved} onClose={closeModal} />
      )}
      {modal === "edit" && selectedMeeting && (
        <MeetingFormModal
          meeting={selectedMeeting}
          onSave={onSaved}
          onClose={closeModal}
        />
      )}
      {modal === "archive" && selectedMeeting && (
        <ArchiveModal
          meeting={selectedMeeting}
          onSaved={onSaved}
          onClose={closeModal}
        />
      )}
    </div>
  );
}
