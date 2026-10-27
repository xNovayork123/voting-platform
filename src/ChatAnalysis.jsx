import React, { useState } from 'react';
import './ChatAnalysis.css';
import { useToast } from './Toast';

const API_URL = '/api/chat/analyze/';

// ─── Helpers y constantes de presentación ──────────────────────────────────
// Read a cookie value (used for Django's CSRF token), same helper as DocVault.
const getCookie = (name) => {
  if (!document.cookie) return null;
  const match = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(name + '='));
  return match ? decodeURIComponent(match.substring(name.length + 1)) : null;
};

const HOUR_LABELS = ['12a', '3a', '6a', '9a', '12p', '3p', '6p', '9p'];  // eje X del gráfico de barras

const SENTIMENT_COLORS = {
  positive: '#10b981',
  neutral: '#94a3b8',
  negative: '#ef4444',
};

// Convierte hora 0-23 (formato del backend) a "9 AM" / "9 PM" para mostrar.
const formatHour = (h) => {
  if (h === null || h === undefined) return '—';
  const period = h < 12 ? 'AM' : 'PM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12} ${period}`;
};

const ChatAnalysis = ({ user, onLogout, onNavigate }) => {
  const toast = useToast();
  // ─── Estado del componente ─────────────────────────────────────────────
  const [mode, setMode] = useState('paste'); // 'paste' | 'upload'
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);  // respuesta cruda de la API, o null si no se analizó nada todavía

  // ─── Llamada a la API: POST /api/chat/analyze/ ─────────────────────────
  const analyze = async () => {
    if (mode === 'upload' && !file) return toast.error('Please choose a .txt file.');
    if (mode === 'paste' && !text.trim()) return toast.error('Please paste some chat text.');

    // Un mismo FormData sirve para los 2 modos; el backend distingue por el
    // nombre del campo ("file" vs "text"), no por una bandera explícita.
    const form = new FormData();
    if (mode === 'upload') form.append('file', file);
    else form.append('text', text);

    setLoading(true);
    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },  // no es un <form> HTML normal, hay que mandarlo a mano
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.error || 'Analysis failed.');
        return;
      }
      setResult(data);
      toast.success('Chat analyzed.');
    } catch {
      toast.error('Server error during analysis.');
    } finally {
      setLoading(false);
    }
  };

  // Máximo de mensajes en una sola hora; se usa para escalar la altura de las
  // barras del gráfico a un %. Math.max(1, ...) evita dividir por 0 si todas
  // las horas tuvieran 0 mensajes.
  const maxHourCount = result
    ? Math.max(1, ...result.activity_by_hour.map((h) => h.count))
    : 1;

  return (
    <div className="chat-analysis">
      {/* ─── Encabezado ─── */}
      <header className="ca-topbar">
        <div className="ca-title">
          <span className="ca-logo">💬</span>
          <div>
            <h1>Chat Analysis</h1>
            <p>WhatsApp frequency &amp; sentiment</p>
          </div>
        </div>
        <div className="ca-actions">
          <button className="ca-link" onClick={() => onNavigate('dashboard')}>← Dashboard</button>
          <button className="ca-logout" onClick={onLogout}>Sign Out</button>
        </div>
      </header>

      <main className="ca-main">
        {/* ─── Sección de entrada: pegar texto o subir un .txt ─── */}
        <section className="ca-card ca-input-card">
          <div className="ca-tabs">
            <button
              className={mode === 'paste' ? 'ca-tab active' : 'ca-tab'}
              onClick={() => setMode('paste')}
            >
              Paste text
            </button>
            <button
              className={mode === 'upload' ? 'ca-tab active' : 'ca-tab'}
              onClick={() => setMode('upload')}
            >
              Upload .txt
            </button>
          </div>

          {mode === 'paste' ? (
            <textarea
              className="ca-textarea"
              placeholder={'Paste an exported WhatsApp chat here, e.g.\n1/1/24, 9:05 AM - Alice: Happy new year!'}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          ) : (
            <label className="ca-file-drop">
              <input
                type="file"
                accept=".txt"
                onChange={(e) => setFile(e.target.files[0] || null)}
              />
              <span>{file ? `📄 ${file.name}` : 'Click to choose a WhatsApp .txt export'}</span>
            </label>
          )}

          <div className="ca-input-footer">
            <span className="ca-hint">
              In WhatsApp: open a chat → ⋮ → More → Export chat → Without media.
            </span>
            <button className="ca-analyze-btn" onClick={analyze} disabled={loading}>
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </section>

        {/* ─── Resultados: solo se muestran después de un análisis exitoso ─── */}
        {result && (
          <>
            {/* Tarjetas resumen */}
            <section className="ca-cards">
              <div className="ca-stat">
                <span className="ca-stat-val">{result.summary.total_messages}</span>
                <span className="ca-stat-label">Messages</span>
              </div>
              <div className="ca-stat">
                <span className="ca-stat-val">{result.summary.participants.length}</span>
                <span className="ca-stat-label">Participants</span>
              </div>
              <div className="ca-stat">
                <span className="ca-stat-val">{result.summary.avg_messages_per_day}</span>
                <span className="ca-stat-label">Avg / day</span>
              </div>
              <div className="ca-stat">
                <span className="ca-stat-val">{formatHour(result.peak_hour)}</span>
                <span className="ca-stat-label">Peak hour</span>
              </div>
            </section>

            {/* Gráfico de barras: actividad por hora (24 barras, la pico resaltada en naranja) */}
            <section className="ca-card">
              <h2>Activity by hour</h2>
              <p className="ca-sub">When messages are most frequent across the day.</p>
              <div className="ca-bars">
                {result.activity_by_hour.map((h) => (
                  <div className="ca-bar-col" key={h.hour} title={`${formatHour(h.hour)}: ${h.count}`}>
                    <div
                      className={h.hour === result.peak_hour ? 'ca-bar peak' : 'ca-bar'}
                      style={{ height: `${(h.count / maxHourCount) * 100}%` }}
                    />
                  </div>
                ))}
              </div>
              <div className="ca-bar-axis">
                {HOUR_LABELS.map((l) => <span key={l}>{l}</span>)}
              </div>
            </section>

            {/* Barras de sentimiento: % positivo / neutral / negativo */}
            <section className="ca-card">
              <h2>Sentiment</h2>
              <p className="ca-sub">
                Overall tone: <strong className={`ca-tone ${result.sentiment.overall}`}>
                  {result.sentiment.overall}
                </strong> ({result.sentiment.analyzed} messages analyzed)
              </p>
              <div className="ca-sentiment">
                {['positive', 'neutral', 'negative'].map((key) => (
                  <div className="ca-sent-row" key={key}>
                    <span className="ca-sent-label">{key}</span>
                    <div className="ca-sent-track">
                      <div
                        className="ca-sent-fill"
                        style={{
                          width: `${result.sentiment[`${key}_pct`]}%`,
                          background: SENTIMENT_COLORS[key],
                        }}
                      />
                    </div>
                    <span className="ca-sent-val">
                      {result.sentiment[key]} · {result.sentiment[`${key}_pct`]}%
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* Tabla por participante: cruza frecuencia (per_participant) con
                tono (per_participant_sentiment), buscando por nombre */}
            <section className="ca-card">
              <h2>Per participant</h2>
              <div className="ca-table-wrap">
                <table className="ca-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Messages</th>
                      <th>Avg / day</th>
                      <th>Active hours</th>
                      <th>Tone</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.per_participant.map((p) => {
                      // Frecuencia y sentimiento vienen en 2 arrays separados
                      // del backend; se cruzan aquí por nombre de participante.
                      const tone = result.per_participant_sentiment
                        .find((s) => s.name === p.name);
                      return (
                        <tr key={p.name}>
                          <td>{p.name}</td>
                          <td>{p.messages}</td>
                          <td>{p.avg_per_day}</td>
                          <td>{p.active_hours.map(formatHour).join(', ')}</td>
                          <td>
                            <span className={`ca-tone ${tone ? tone.overall : 'neutral'}`}>
                              {tone ? tone.overall : '—'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
};

export default ChatAnalysis;
