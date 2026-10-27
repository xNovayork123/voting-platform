import React, { useState } from 'react';
import './CreateBallot.css';
import { CATEGORIES } from './ballotUtils';

const API_URL = '/api';

// Convert an ISO/UTC datetime to a value usable by <input type="datetime-local">.
function toLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d - tz).toISOString().slice(0, 16);
}

const CreateBallot = ({ onCreated, onSaved, onCancel, ballot = null }) => {
  const isEdit = !!ballot;

  const [title, setTitle] = useState(ballot ? ballot.title : '');
  const [description, setDescription] = useState(ballot ? (ballot.description || '') : '');
  const [options, setOptions] = useState(ballot ? [...ballot.options] : ['', '']);
  const [category, setCategory] = useState(ballot ? (ballot.category || 'general') : 'general');
  const [startDate, setStartDate] = useState(ballot ? toLocalInput(ballot.start_date) : '');
  const [endDate, setEndDate] = useState(ballot ? toLocalInput(ballot.end_date) : '');
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

    const payload = {
      title: title.trim(),
      description: description.trim(),
      options: filledOptions,
      category,
      start_date: new Date(startDate).toISOString(),
      end_date: new Date(endDate).toISOString(),
      status: isEdit ? ballot.status : 'open',
    };

    setIsLoading(true);
    try {
      const res = await fetch(
        isEdit ? `${API_URL}/ballots/${ballot.id}/` : `${API_URL}/ballots/`,
        {
          method: isEdit ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        const errMsg = typeof data === 'object' ? Object.values(data).flat().join(' ') : 'Could not save ballot.';
        setError(errMsg);
        return;
      }
      if (isEdit) { onSaved && onSaved(data); } else { onCreated && onCreated(data); }
    } catch (err) {
      setError('Server error. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="create-overlay">
      <div className="create-modal">
        <div className="create-header">
          <h2>{isEdit ? 'Edit Ballot' : 'Create New Ballot'}</h2>
          <button className="close-button" onClick={onCancel}>✕</button>
        </div>

        {error && <div className="create-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field-group">
            <label>Title *</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="Ballot title" required />
          </div>
          <div className="field-group">
            <label>Category</label>
            <select value={category} onChange={e => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div className="field-group">
            <label>Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" rows={3} />
          </div>
          <div className="field-group">
            <label>Options * <span className="hint">(min 2, max 8)</span></label>
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
          <div className="date-row">
            <div className="field-group">
              <label>Start Date *</label>
              <input type="datetime-local" value={startDate} onChange={e => setStartDate(e.target.value)} required />
            </div>
            <div className="field-group">
              <label>End Date *</label>
              <input type="datetime-local" value={endDate} onChange={e => setEndDate(e.target.value)} required />
            </div>
          </div>
          <div className="create-actions">
            <button type="button" className="cancel-button" onClick={onCancel}>Cancel</button>
            <button type="submit" className="submit-button" disabled={isLoading}>
              {isLoading ? 'Saving...' : (isEdit ? 'Save Changes' : 'Create Ballot')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateBallot;
