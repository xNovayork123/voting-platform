import React, { useEffect, useState } from 'react';
import './Dashboard.css';
import Sidebar from './Sidebar';
import { getEffectiveStatus, formatTimeRemaining } from './ballotUtils';

const API_URL = '/api';

const Dashboard = ({ user, onLogout, onNavigate }) => {
  const [ballots, setBallots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    fetch(`${API_URL}/ballots/`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => { setBallots(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(t);
  }, []);

  const totalVotes = ballots.reduce((sum, b) => sum + (b.vote_count || 0), 0);
  const openBallots = ballots.filter(b => getEffectiveStatus(b, now) === 'open');
  const activeBallots = openBallots.length;
  const closedBallots = ballots.length - activeBallots;

  return (
    <div className="dashboard">
      <Sidebar user={user} active="dashboard" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="main-content">
        <header className="main-header">
          <div>
            <h1>Dashboard</h1>
            <p className="header-sub">Welcome back, {user.username || user.email} 👋</p>
          </div>
          <button className="new-ballot-btn" onClick={() => onNavigate('create')}>
            {user.is_admin ? '+ New Ballot' : '💡 Suggest Ballot'}
          </button>
        </header>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🗳️</div>
            <div className="stat-info">
              <span className="stat-value">{ballots.length}</span>
              <span className="stat-label">Total Ballots</span>
            </div>
          </div>
          <div className="stat-card active-card">
            <div className="stat-icon">✅</div>
            <div className="stat-info">
              <span className="stat-value">{activeBallots}</span>
              <span className="stat-label">Active Ballots</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔒</div>
            <div className="stat-info">
              <span className="stat-value">{closedBallots}</span>
              <span className="stat-label">Closed Ballots</span>
            </div>
          </div>
          <div className="stat-card votes-card">
            <div className="stat-icon">👥</div>
            <div className="stat-info">
              <span className="stat-value">{totalVotes}</span>
              <span className="stat-label">Total Votes</span>
            </div>
          </div>
        </div>

        <section className="section">
          <div className="section-header">
            <h2>Active Ballots</h2>
            <button className="see-all" onClick={() => onNavigate('vote')}>View All →</button>
          </div>
          {loading ? (
            <div className="loading">Loading...</div>
          ) : openBallots.length === 0 ? (
            <div className="empty-state">
              <p>No active ballots yet.</p>
              <button className="new-ballot-btn" onClick={() => onNavigate('create')}>
                {user.is_admin ? 'Create First Ballot' : 'Suggest a Ballot'}
              </button>
            </div>
          ) : (
            <div className="ballot-list">
              {openBallots.map(ballot => (
                <div key={ballot.id} className="ballot-row" onClick={() => onNavigate('vote')}>
                  <div className="ballot-row-left">
                    <span className="ballot-dot" />
                    <div>
                      <p className="ballot-row-title">{ballot.title}</p>
                      <p className="ballot-row-options">{ballot.options.join(' · ')}</p>
                    </div>
                  </div>
                  <div className="ballot-row-right">
                    <span className="row-countdown">⏳ {formatTimeRemaining(ballot.end_date, now)}</span>
                    <span className="badge badge-open">Open</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {ballots.length > 0 && (
          <section className="section">
            <div className="section-header">
              <h2>All Ballots</h2>
            </div>
            <div className="table-wrap">
              <table className="ballots-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Options</th>
                    <th>End Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {ballots.map(ballot => {
                    const eff = getEffectiveStatus(ballot, now);
                    return (
                    <tr key={ballot.id}>
                      <td className="td-title">{ballot.title}</td>
                      <td className="td-options">{ballot.options.length} options</td>
                      <td className="td-date">{new Date(ballot.end_date).toLocaleDateString('en-US')}</td>
                      <td>
                        <span className={`badge badge-${eff}`}>
                          {eff === 'open' ? 'Open' : 'Closed'}
                        </span>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
