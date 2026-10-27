import React, { useEffect, useState } from 'react';
import './FinancePage.css';
import { useToast } from './Toast';
import Sidebar from './Sidebar';

const API_URL = '/api/finance';

const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

const COLORS = ['#1a56db', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

// ---- Small SVG donut chart (same hand-drawn style as ResultsChart) ----
function polarToCartesian(cx, cy, r, angleDeg) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}
function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

function CategoryDonut({ data }) {
  const entries = Object.entries(data || {});
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  const size = 160, cx = 80, cy = 80, r = 58, stroke = 22;

  if (!total) {
    return <div className="chart-empty"><p>No expense data yet</p></div>;
  }

  let angle = 0;
  const segments = entries.map(([label, value], i) => {
    const pct = value / total;
    const seg = { label, value, pct, start: angle, end: angle + pct * 360, color: COLORS[i % COLORS.length] };
    angle = seg.end;
    return seg;
  });

  return (
    <div className="chart-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#eef2f7" strokeWidth={stroke} />
        {segments.map((s, i) =>
          s.pct >= 0.999
            ? <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={s.color} strokeWidth={stroke} />
            : <path key={i} d={describeArc(cx, cy, r, s.start, s.end)} fill="none" stroke={s.color} strokeWidth={stroke} />
        )}
      </svg>
      <ul className="chart-legend">
        {segments.map((s, i) => (
          <li key={i}>
            <span className="legend-dot" style={{ background: s.color }} />
            <span className="legend-label">{s.label}</span>
            <span className="legend-val">{Math.round(s.pct * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const FinancePage = ({ user, onLogout, onNavigate }) => {
  const toast = useToast();

  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState({ income: 0, expense: 0, balance: 0 });
  const [stats, setStats] = useState({ category_totals: {}, this_month: { income: 0, expense: 0 }, last_month: { income: 0, expense: 0 } });
  const [budgets, setBudgets] = useState([]);

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Add / edit transaction modal
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [fType, setFType] = useState('expense');
  const [fAmount, setFAmount] = useState('');
  const [fCategory, setFCategory] = useState('General');
  const [fDescription, setFDescription] = useState('');
  const [fDate, setFDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [fReceipt, setFReceipt] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  // Budget modal
  const [showBudget, setShowBudget] = useState(false);
  const [bCategory, setBCategory] = useState('General');
  const [bLimit, setBLimit] = useState('');

  const categories = ['General', 'Salary', 'Rent', 'Food', 'Transport', 'Bills', 'Other'];

  useEffect(() => { loadData(); }, [search, typeFilter, startDate, endDate]);
  useEffect(() => { loadStats(); loadBudgets(); }, []);

  const loadData = async () => {
    try {
      let url = `${API_URL}/transactions/?type=${typeFilter}`;
      if (search) url += `&q=${encodeURIComponent(search)}`;
      if (startDate) url += `&start=${startDate}`;
      if (endDate) url += `&end=${endDate}`;
      const res = await fetch(url, { credentials: 'include' });
      const data = await res.json();
      setTransactions(data.transactions || []);
      setSummary(data.summary || { income: 0, expense: 0, balance: 0 });
    } catch {
      toast.error('Failed to load transactions.');
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_URL}/stats/`, { credentials: 'include' });
      const data = await res.json();
      setStats(data);
    } catch { /* sessizce geç */ }
  };

  const loadBudgets = async () => {
    try {
      const res = await fetch(`${API_URL}/budgets/`, { credentials: 'include' });
      const data = await res.json();
      setBudgets(data.budgets || []);
    } catch { /* sessizce geç */ }
  };

  const openAdd = () => {
    setEditId(null);
    setFType('expense'); setFAmount(''); setFCategory('General');
    setFDescription(''); setFDate(new Date().toISOString().slice(0, 10)); setFReceipt(null);
    setShowModal(true);
  };

  const openEdit = (t) => {
    setEditId(t.id);
    setFType(t.type); setFAmount(String(t.amount)); setFCategory(t.category);
    setFDescription(t.description || ''); setFDate(t.date); setFReceipt(null);
    setShowModal(true);
  };

  const handleSave = async () => {
    const amountNumber = parseFloat(fAmount);
    if (!fAmount || isNaN(amountNumber) || amountNumber <= 0) {
      return toast.error('Please enter a valid amount greater than 0.');
    }
    if (!fDate) return toast.error('Please select a date.');

    setIsSaving(true);
    try {
      // FormData so we can attach a receipt file
      const fd = new FormData();
      fd.append('type', fType);
      fd.append('amount', amountNumber);
      fd.append('category', fCategory);
      fd.append('description', fDescription);
      fd.append('date', fDate);
      if (fReceipt) fd.append('receipt', fReceipt);

      const url = editId ? `${API_URL}/transactions/${editId}/update/` : `${API_URL}/add/`;
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: fd,
      });
      const data = await res.json();
      if (data.success) {
        toast.success(editId ? 'Transaction updated!' : 'Transaction added!');
        if (data.warning) toast.error(data.warning); // bütçe uyarısı
        setShowModal(false);
        loadData(); loadStats();
      } else {
        toast.error(data.error || 'Could not save transaction.');
      }
    } catch {
      toast.error('Server error while saving.');
    } finally {
      setIsSaving(false);
    }
  };

  const deleteTransaction = async (id) => {
    if (!window.confirm('Delete this transaction?')) return;
    try {
      const res = await fetch(`${API_URL}/transactions/${id}/`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      });
      if (res.ok) {
        toast.success('Deleted.');
        loadData(); loadStats();
      } else {
        toast.error('Delete failed.');
      }
    } catch {
      toast.error('Server error.');
    }
  };

  const saveBudget = async () => {
    const limitNumber = parseFloat(bLimit);
    if (!bLimit || isNaN(limitNumber) || limitNumber <= 0) {
      return toast.error('Please enter a valid limit.');
    }
    try {
      const res = await fetch(`${API_URL}/budgets/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ category: bCategory, monthly_limit: limitNumber }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Budget saved!');
        setShowBudget(false);
        setBLimit('');
        loadBudgets();
      } else {
        toast.error(data.error || 'Could not save budget.');
      }
    } catch {
      toast.error('Server error.');
    }
  };

  const exportCsv = () => {
    window.open(`${API_URL}/export/`, '_blank');
  };

  const formatMoney = (value) =>
    Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Aylık karşılaştırma yüzdesi
  const expenseDiff = () => {
    const now = stats.this_month.expense;
    const prev = stats.last_month.expense;
    if (!prev) return null;
    const pct = ((now - prev) / prev) * 100;
    return pct;
  };
  const diff = expenseDiff();

  return (
    <div className="vote-layout">
      <Sidebar user={user} active="finance" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="vote-main" style={{ marginLeft: '240px', padding: '32px', flex: 1 }}>
        <header className="vote-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Finance</h1>
            <p className="header-sub">{transactions.length} transaction(s)</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="finance-btn-ghost" onClick={exportCsv}>⬇ Export CSV</button>
            <button className="finance-btn-ghost" onClick={() => setShowBudget(true)}>🎯 Budget</button>
            <button className="new-ballot-btn" onClick={openAdd}>+ Add Transaction</button>
          </div>
        </header>

        {/* SUMMARY CARDS */}
        <div className="finance-summary">
          <div className="summary-card income">
            <p className="summary-label">Total Income</p>
            <p className="summary-value">+{formatMoney(summary.income)}</p>
          </div>
          <div className="summary-card expense">
            <p className="summary-label">Total Expense</p>
            <p className="summary-value">-{formatMoney(summary.expense)}</p>
          </div>
          <div className="summary-card balance">
            <p className="summary-label">Balance</p>
            <p className="summary-value">{formatMoney(summary.balance)}</p>
          </div>
        </div>

        {/* CHARTS + MONTHLY COMPARISON */}
        <div className="finance-insights">
          <div className="insight-card">
            <h3>Expenses by Category</h3>
            <CategoryDonut data={stats.category_totals} />
          </div>
          <div className="insight-card">
            <h3>This Month vs Last Month</h3>
            <div className="month-compare">
              <div className="month-row">
                <span className="month-name">Last month</span>
                <span className="month-exp">-{formatMoney(stats.last_month.expense)}</span>
                <span className="month-inc">+{formatMoney(stats.last_month.income)}</span>
              </div>
              <div className="month-row">
                <span className="month-name">This month</span>
                <span className="month-exp">-{formatMoney(stats.this_month.expense)}</span>
                <span className="month-inc">+{formatMoney(stats.this_month.income)}</span>
              </div>
              {diff !== null && (
                <p className={`month-diff ${diff > 0 ? 'up' : 'down'}`}>
                  {diff > 0 ? '▲' : '▼'} Spending {diff > 0 ? 'up' : 'down'} {Math.abs(diff).toFixed(0)}% vs last month
                </p>
              )}
            </div>
          </div>
        </div>

        {/* TOOLBAR */}
        <div className="finance-toolbar">
          <input type="text" placeholder="Search..." className="search-input"
            value={search} onChange={(e) => setSearch(e.target.value)} />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="income">Income</option>
            <option value="expense">Expense</option>
          </select>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} title="Start date" />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} title="End date" />
        </div>

        {/* TRANSACTION LIST */}
        {transactions.length === 0 ? (
          <div className="empty-state">
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📭</div>
            <h3>No transactions yet</h3>
            <p>Add your first income or expense to get started.</p>
          </div>
        ) : (
          <table className="finance-table">
            <thead>
              <tr>
                <th>Date</th><th>Description</th><th>Category</th><th>Type</th>
                <th style={{ textAlign: 'right' }}>Amount</th><th>Receipt</th><th></th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description || '-'}</td>
                  <td>{t.category}</td>
                  <td><span className={`type-badge ${t.type}`}>{t.type === 'income' ? 'Income' : 'Expense'}</span></td>
                  <td style={{ textAlign: 'right', color: t.type === 'income' ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                    {t.type === 'income' ? '+' : '-'}{formatMoney(t.amount)}
                  </td>
                  <td>{t.receipt ? <a href={t.receipt} target="_blank" rel="noreferrer">📎 View</a> : '-'}</td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="row-btn" onClick={() => openEdit(t)}>✏️</button>
                    <button className="row-btn danger" onClick={() => deleteTransaction(t.id)}>🗑</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>

      {/* ADD / EDIT MODAL */}
      {showModal && (
        <div className="create-overlay">
          <div className="create-modal">
            <div className="create-header">
              <h2>{editId ? 'Edit Transaction' : 'Add Transaction'}</h2>
              <button className="close-button" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="field-group">
              <label>Type</label>
              <select value={fType} onChange={(e) => setFType(e.target.value)}>
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </div>
            <div className="field-group">
              <label>Amount</label>
              <input type="number" min="0" step="0.01" value={fAmount}
                onChange={(e) => setFAmount(e.target.value)} placeholder="e.g. 100.00" />
            </div>
            <div className="field-group">
              <label>Category</label>
              <select value={fCategory} onChange={(e) => setFCategory(e.target.value)}>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="field-group">
              <label>Description</label>
              <input type="text" value={fDescription}
                onChange={(e) => setFDescription(e.target.value)} placeholder="e.g. Monthly salary" />
            </div>
            <div className="field-group">
              <label>Date</label>
              <input type="date" value={fDate} onChange={(e) => setFDate(e.target.value)} />
            </div>
            <div className="field-group">
              <label>Receipt / Invoice (optional)</label>
              <input type="file" onChange={(e) => setFReceipt(e.target.files[0])} />
            </div>
            <div className="create-actions">
              <button className="cancel-button" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="submit-button" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving...' : (editId ? 'Update' : 'Add')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* BUDGET MODAL */}
      {showBudget && (
        <div className="create-overlay">
          <div className="create-modal">
            <div className="create-header">
              <h2>Set Monthly Budget</h2>
              <button className="close-button" onClick={() => setShowBudget(false)}>✕</button>
            </div>
            <div className="field-group">
              <label>Category</label>
              <select value={bCategory} onChange={(e) => setBCategory(e.target.value)}>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="field-group">
              <label>Monthly limit</label>
              <input type="number" min="0" step="0.01" value={bLimit}
                onChange={(e) => setBLimit(e.target.value)} placeholder="e.g. 1000" />
            </div>
            {budgets.length > 0 && (
              <div className="budget-existing">
                <h4>Current budgets</h4>
                <ul className="budget-list">
                  {budgets.map((b) => (
                    <li key={b.id}><span>{b.category}</span><span>{formatMoney(b.monthly_limit)}</span></li>
                  ))}
                </ul>
              </div>
            )}
            <div className="create-actions">
              <button className="cancel-button" onClick={() => setShowBudget(false)}>Cancel</button>
              <button className="submit-button" onClick={saveBudget}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinancePage;
