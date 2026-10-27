import React, { useState } from 'react';
import './CreateBallot.css';

const API_URL = '/api';

const SuggestBallot = ({ onSent, onCancel }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [options, setOptions] = useState(['', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleOptionChange = (index, value) => {
    const updated = [...options];
    updated[index] = value;
    setOptions(updated);
  };

  const addOption = () => { if (options.length < 8) setOptions([...options, '']); };
  const removeOption = (index) => { if (options.length > 2) setOptions(options.filter((_, i) => i !== index)); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const filledOptions = options.map(o => o.trim()).filter(o => o !== '');
    if (filledOptions.length < 2) { setError('At least 2 options are required.'); return; }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/suggestions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ title: title.trim(), description: description.trim(), options: filledOptions }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || 'Could not send suggestion.'); return; }
      onSent();
    } catch (err) {
      setError('Server error.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="create-overlay">
      <div className="create-modal">
        <div className="create-header">
          <h2>💡 Suggest a Ballot</h2>
          <button className="close-button" onClick={onCancel}>✕</button>
        </div>
        <p style={{ color: '#6b7280', fontSize: '0.88rem', marginBottom: '16px' }}>
          Your suggestion will be reviewed by an admin before being published.
        </p>

        {error && <div className="create-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field-group">
            <label>Title *</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="Ballot title" required />
          </div>
          <div className="field-group">
            <label>Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" rows={3} />
          </div>
          <div className="field-group">
            <label>Options * <span className="hint">(min 2)</span></label>
            {options.map((opt, index) => (
              <div key={index} className="option-row">
                <input type="text" value={opt} onChange={e => handleOptionChange(index, e.target.value)} placeholder={`Option ${index + 1}`} />
                {options.length > 2 && (
                  <button type="button" className="remove-option" onClick={() => removeOption(index)}>✕</button>
                )}
              </div>
            ))}
            {options.length < 8 && (
              <button type="button" className="add-option" onClick={addOption}>+ Add Option</button>
            )}
          </div>
          <div className="create-actions">
            <button type="button" className="cancel-button" onClick={onCancel}>Cancel</button>
            <button type="submit" className="submit-button" disabled={isLoading}>
              {isLoading ? 'Sending...' : '💡 Send Suggestion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SuggestBallot;
