import React, { useEffect, useState } from 'react';
import './AdminSuggestions.css';

const API_URL = '/api';

const AdminSuggestions = ({ onClose }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch(`${API_URL}/suggestions/`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => { setSuggestions(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleAction = async (id, action) => {
    const res = await fetch(`${API_URL}/suggestions/${id}/action/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ action }),
    });
    const data = await res.json();
    setMessage(data.message || 'Action completed.');
    setSuggestions(prev => prev.map(s => s.id === id ? { ...s, status: action === 'approve' ? 'approved' : 'rejected' } : s));
  };

  return (
    <div className="create-overlay">
      <div className="suggestions-modal">
        <div className="create-header">
          <h2>📋 Ballot Suggestions</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        {message && <div className="success-box">{message}</div>}

        {loading ? (
          <p style={{ color: '#6b7280', padding: '16px' }}>Loading...</p>
        ) : suggestions.length === 0 ? (
          <p style={{ color: '#6b7280', padding: '16px', textAlign: 'center' }}>No suggestions yet.</p>
        ) : (
          <div className="suggestions-list">
            {suggestions.map(s => (
              <div key={s.id} className={`suggestion-card status-${s.status}`}>
                <div className="suggestion-top">
                  <div>
                    <p className="suggestion-title">{s.title}</p>
                    <p className="suggestion-by">Suggested by: {s.suggested_by}</p>
                    {s.description && <p className="suggestion-desc">{s.description}</p>}
                    <p className="suggestion-options">Options: {s.options.join(', ')}</p>
                  </div>
                  <span className={`badge badge-${s.status}`}>
                    {s.status === 'pending' ? 'Pending' : s.status === 'approved' ? 'Approved' : 'Rejected'}
                  </span>
                </div>
                {s.status === 'pending' && (
                  <div className="suggestion-actions">
                    <button className="approve-btn" onClick={() => handleAction(s.id, 'approve')}>✓ Approve</button>
                    <button className="reject-btn" onClick={() => handleAction(s.id, 'reject')}>✕ Reject</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminSuggestions;
