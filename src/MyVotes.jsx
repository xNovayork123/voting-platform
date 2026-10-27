import React, { useEffect, useState } from "react";
import "./VotePage.css";
import "./MyVotes.css";
import Sidebar from "./Sidebar";
import { getEffectiveStatus } from "./ballotUtils";

const API_URL = "/api";

const MyVotes = ({ user, onLogout, onNavigate }) => {
  const [votes, setVotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [now] = useState(new Date());

  useEffect(() => {
    fetch(`${API_URL}/my-votes/`, { credentials: "include" })
      .then(res => res.json())
      .then(data => { setVotes(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="vote-layout">
      <Sidebar user={user} active="myvotes" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="vote-main">
        <header className="vote-header">
          <div>
            <h1>My Votes</h1>
            <p className="header-sub">Ballots you have voted on</p>
          </div>
        </header>

        {loading ? (
          <div className="empty-state"><p>Loading...</p></div>
        ) : votes.length === 0 ? (
          <div className="empty-state">
            <p>You haven't voted on any ballots yet.</p>
            <button className="new-ballot-btn" onClick={() => onNavigate('vote')}>Go to Ballots</button>
          </div>
        ) : (
          <div className="myvotes-list">
            {votes.map(v => {
              const eff = getEffectiveStatus(v, now);
              return (
                <div key={v.ballot_id} className="myvote-row">
                  <div className="myvote-info">
                    <p className="myvote-title">{v.title}</p>
                    <p className="myvote-choice">Your choice: <strong>{v.option}</strong></p>
                  </div>
                  <span className={`badge badge-${eff}`}>{eff === 'open' ? 'Open' : 'Closed'}</span>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

export default MyVotes;
