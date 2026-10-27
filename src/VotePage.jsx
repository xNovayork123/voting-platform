import React, { useEffect, useState } from "react";
import "./VotePage.css";
import { useToast } from "./Toast";
import { getEffectiveStatus, formatTimeRemaining, isEndingSoon, CATEGORIES, categoryLabel } from "./ballotUtils";
import ResultsChart from "./ResultsChart";
import CreateBallot from "./CreateBallot";
import Sidebar from "./Sidebar";

const API_URL = "/api";

const VotePage = ({ user, onLogout, onNavigate }) => {
  const toast = useToast();
  const [ballots, setBallots] = useState([]);
  const [results, setResults] = useState({});
  const [votedBallots, setVotedBallots] = useState({});
  const [error, setError] = useState("");

  // Search + filters
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // all | open | closed
  const [categoryFilter, setCategoryFilter] = useState("all");

  // Admin: ballot being edited
  const [editing, setEditing] = useState(null);

  // Live "now" so countdowns and badges stay current
  const [now, setNow] = useState(new Date());

  const loadBallots = async () => {
    try {
      const res = await fetch(`${API_URL}/ballots/`, { credentials: "include" });
      const data = await res.json();
      setBallots(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    }
  };

  const closeBallot = async (ballot) => {
    try {
      const res = await fetch(`${API_URL}/ballots/${ballot.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ status: "closed" }),
      });
      if (!res.ok) { const d = await res.json(); toast.error(d.error || "Could not close ballot."); return; }
      toast.success("Ballot closed.");
      loadBallots();
    } catch (err) { toast.error("Server error."); }
  };

  const deleteBallot = async (ballot) => {
    if (!window.confirm(`Delete "${ballot.title}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API_URL}/ballots/${ballot.id}/`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) { const d = await res.json(); toast.error(d.error || "Could not delete ballot."); return; }
      toast.success("Ballot deleted.");
      loadBallots();
    } catch (err) { toast.error("Server error."); }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const bRes = await fetch(`${API_URL}/ballots/`, { credentials: "include" });
        const bData = await bRes.json();
        if (active) setBallots(Array.isArray(bData) ? bData : []);

        const mRes = await fetch(`${API_URL}/my-votes/`, { credentials: "include" });
        const mData = await mRes.json();
        if (!active || !Array.isArray(mData)) return;

        const voted = {};
        mData.forEach(v => { voted[v.ballot_id] = v.option; });
        setVotedBallots(voted);

        const entries = await Promise.all(mData.map(async v => {
          try {
            const r = await fetch(`${API_URL}/ballots/${v.ballot_id}/results/`, { credentials: "include" });
            return [v.ballot_id, await r.json()];
          } catch {
            return null;
          }
        }));
        if (active) {
          const rmap = {};
          entries.forEach(e => { if (e) rmap[e[0]] = e[1]; });
          setResults(prev => ({ ...prev, ...rmap }));
        }
      } catch (err) {
        console.error(err);
      }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(t);
  }, []);

  const vote = async (ballotId, option) => {
    setError("");
    try {
      const res = await fetch(`${API_URL}/ballots/${ballotId}/vote/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ option }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Could not cast vote.");
        toast.error(data.error || "Could not cast vote.");
        return;
      }
      setVotedBallots(prev => ({ ...prev, [ballotId]: option }));
      toast.success("Your vote has been recorded.");
      const resultRes = await fetch(`${API_URL}/ballots/${ballotId}/results/`, { credentials: "include" });
      const resultData = await resultRes.json();
      setResults(prev => ({ ...prev, [ballotId]: resultData }));
    } catch (err) {
      setError("Server error.");
      toast.error("Server error.");
    }
  };

  const filtered = ballots.filter(b => {
    const eff = getEffectiveStatus(b, now);
    if (statusFilter !== "all" && eff !== statusFilter) return false;
    if (categoryFilter !== "all" && (b.category || "general") !== categoryFilter) return false;
    if (query.trim()) {
      const q = query.toLowerCase();
      const hay = `${b.title} ${b.description || ""} ${(b.options || []).join(" ")}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  const filterChips = [
    { key: "all", label: "All" },
    { key: "open", label: "Active" },
    { key: "closed", label: "Closed" },
  ];

  return (
    <div className="vote-layout">
      <Sidebar user={user} active="vote" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="vote-main">
        <header className="vote-header">
          <div>
            <h1>Ballots</h1>
            <p className="header-sub">Cast your vote on active ballots</p>
          </div>
          <button className="new-ballot-btn" onClick={() => onNavigate('create')}>
            {user.is_admin ? '+ New Ballot' : '💡 Suggest Ballot'}
          </button>
        </header>

        {ballots.length > 0 && (
          <div className="ballots-toolbar">
            <div className="search-wrap">
              <span className="search-icon">🔍</span>
              <input
                className="search-input"
                type="text"
                placeholder="Search by title, description or option..."
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
              {query && (
                <button className="search-clear" onClick={() => setQuery("")} aria-label="Clear">✕</button>
              )}
            </div>
            <div className="filter-chips">
              {filterChips.map(c => (
                <button
                  key={c.key}
                  className={`chip ${statusFilter === c.key ? 'chip-active' : ''}`}
                  onClick={() => setStatusFilter(c.key)}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <select
              className="category-filter"
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
            >
              <option value="all">All categories</option>
              {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
        )}

        {error && <div className="error-box">{error}</div>}

        {ballots.length === 0 ? (
          <div className="empty-state">
            <p>No ballots found.</p>
            <button className="new-ballot-btn" onClick={() => onNavigate('create')}>
              {user.is_admin ? 'Create First Ballot' : 'Suggest a Ballot'}
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <p>No ballots match your search.</p>
          </div>
        ) : (
          <div className="ballots-grid">
            {filtered.map(ballot => {
              const eff = getEffectiveStatus(ballot, now);
              const soon = eff === 'open' && isEndingSoon(ballot.end_date, now);
              const remaining = formatTimeRemaining(ballot.end_date, now);
              const closed = eff === 'closed';
              return (
                <div key={ballot.id} className="ballot-card">
                  <div className="card-header">
                    <h2>{ballot.title}</h2>
                    <span className={`badge badge-${eff} ${soon ? 'badge-soon' : ''}`}>
                      {closed ? 'Closed' : (soon ? 'Ending soon' : 'Open')}
                    </span>
                  </div>

                  <div className="card-meta">
                    <span className="cat-tag">{categoryLabel(ballot.category)}</span>
                    <span className={`countdown ${soon ? 'countdown-soon' : ''} ${closed ? 'countdown-ended' : ''}`}>
                      ⏳ {closed ? 'Voting ended' : remaining}
                    </span>
                  </div>

                  {ballot.description && <p className="card-desc">{ballot.description}</p>}

                  <div className="options-grid">
                    {ballot.options.map(option => (
                      <button
                        key={option}
                        className={`option-btn ${votedBallots[ballot.id] === option ? 'voted' : ''}`}
                        onClick={() => vote(ballot.id, option)}
                        disabled={!!votedBallots[ballot.id] || closed}
                      >
                        {votedBallots[ballot.id] === option ? '✓ ' : ''}{option}
                      </button>
                    ))}
                  </div>

                  {results[ballot.id] && (
                    <div className="results-box">
                      <p className="results-title">Results</p>
                      <ResultsChart
                        results={results[ballot.id].results}
                        total={results[ballot.id].total_votes}
                      />
                    </div>
                  )}

                  {user.is_admin && (
                    <div className="admin-actions">
                      <button className="admin-btn" onClick={() => setEditing(ballot)}>Edit</button>
                      {!closed && (
                        <button className="admin-btn" onClick={() => closeBallot(ballot)}>Close</button>
                      )}
                      <button className="admin-btn admin-btn-danger" onClick={() => deleteBallot(ballot)}>Delete</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>

      {editing && (
        <CreateBallot
          ballot={editing}
          onSaved={() => { setEditing(null); toast.success('Ballot updated.'); loadBallots(); }}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
};

export default VotePage;
