import React, { useEffect, useState, useRef } from 'react';
import './DocVault.css';
import { useToast } from './Toast';
import Sidebar from './Sidebar';

const API_URL = '/api/docvault';

const DocVault = ({ user, onLogout, onNavigate }) => {
  const toast = useToast();
  const [docs, setDocs] = useState([]);
  const [categories, setCategories] = useState(["General", "Work", "Personal", "Finance", "Archive"]);
  const [activeCategory, setActiveCategory] = useState('All');
  const [viewMode, setViewMode] = useState('grid');
  const [search, setSearch] = useState('');
  
  // Modals
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadCat, setUploadCat] = useState('General');
  const [uploadTags, setUploadTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadData();
  }, [activeCategory, search]);

  const loadData = async () => {
    try {
      let url = `${API_URL}/documents/?category=${encodeURIComponent(activeCategory)}`;
      if (search) url += `&q=${encodeURIComponent(search)}`;
      const res = await fetch(url, { credentials: 'include' });
      const data = await res.json();
      setDocs(data.documents || []);
      setCategories(data.categories || []);
    } catch (err) {
      toast.error('Failed to load documents.');
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return toast.error('Please select a file');
    setIsUploading(true);
    const form = new FormData();
    form.append('file', uploadFile);
    form.append('category', uploadCat);
    form.append('tags', uploadTags);

    // Helper to get the CSRF token from cookies
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

    try {
      const res = await fetch(`${API_URL}/upload/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken') // <-- ADD THIS HEADER
        },
        body: form
      });
      const data = await res.json();
      if (data.success) {
        toast.success('File uploaded!');
        setShowUpload(false);
        setUploadFile(null);
        loadData();
      } else {
        toast.error(data.error || 'Upload failed');
      }
    } catch {
      toast.error('Server error during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDoc = async (id) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      const res = await fetch(`${API_URL}/documents/${id}/`, { method: 'DELETE', credentials: 'include' });
      if (res.ok) {
        toast.success('Deleted successfully');
        loadData();
      } else {
        toast.error('Delete failed');
      }
    } catch {
      toast.error('Server error.');
    }
  };

  const handleDownload = async (id, filename) => {
    toast.info('Starting download...', 1500);
    try {
      const res = await fetch(`${API_URL}/download/${id}/`, {
        method: 'GET',
        credentials: 'include', // Ensures your Django session cookie is sent!
      });
      
      if (!res.ok) {
        toast.error('File not found or access denied.');
        return;
      }

      // Convert the response into a file blob
      const blob = await res.blob();
      
      // Create a temporary hidden link to trigger the browser's download prompt
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename; // Forces the browser to download instead of open
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Server error during download.');
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="vote-layout">
      {/* SIDEBAR - Integrated with your Company Portal navigation */}
      <Sidebar user={user} active="docvault" onLogout={onLogout} onNavigate={onNavigate}>
        {/* DocVault Categories */}
        <div style={{ padding: '0 12px', marginTop: '20px' }}>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '8px', paddingLeft: '4px' }}>CATEGORIES</p>
          <button className={`nav-item ${activeCategory === 'All' ? 'active' : ''}`} onClick={() => setActiveCategory('All')}>
            📂 All Documents
          </button>
          {categories.map(cat => (
            <button key={cat} className={`nav-item ${activeCategory === cat ? 'active' : ''}`} onClick={() => setActiveCategory(cat)}>
              📄 {cat}
            </button>
          ))}
        </div>
      </Sidebar>

      {/* MAIN CONTENT */}
      <main className="vote-main" style={{ marginLeft: '240px', padding: '32px', flex: 1 }}>
        <header className="vote-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <div>
            <h1>{activeCategory === 'All' ? 'All Documents' : activeCategory}</h1>
            <p className="header-sub">{docs.length} document(s)</p>
          </div>
          <button className="new-ballot-btn" onClick={() => setShowUpload(true)}>
            ↑ Upload File
          </button>
        </header>

        {/* TOOLBAR */}
        <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
          <input 
            type="text" 
            placeholder="Search documents..." 
            className="search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: 1, padding: '10px 16px', borderRadius: '8px', border: '1px solid #ddd' }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={() => setViewMode('grid')} style={{ padding: '8px 12px', borderRadius: '8px', cursor: 'pointer', background: viewMode === 'grid' ? '#e2e8f0' : '#fff' }}>▦</button>
            <button onClick={() => setViewMode('list')} style={{ padding: '8px 12px', borderRadius: '8px', cursor: 'pointer', background: viewMode === 'list' ? '#e2e8f0' : '#fff' }}>☰</button>
          </div>
        </div>

        {/* GRID */}
        {docs.length === 0 ? (
          <div className="empty-state">
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📭</div>
            <h3>Nothing here yet</h3>
            <p>Upload your first document to get started.</p>
          </div>
        ) : (
          <div className={`doc-grid ${viewMode === 'list' ? 'list-view' : ''}`} style={{ display: 'grid', gridTemplateColumns: viewMode === 'grid' ? 'repeat(auto-fill, minmax(220px, 1fr))' : '1fr', gap: '16px' }}>
            {docs.map(doc => (
              <div key={doc.id} style={{ background: '#fff', padding: '16px', borderRadius: '12px', border: '1px solid #e5e7eb', display: 'flex', flexDirection: viewMode === 'grid' ? 'column' : 'row', alignItems: viewMode === 'list' ? 'center' : 'flex-start', gap: '12px' }}>
                <div style={{ fontSize: '2rem' }}>{doc.icon}</div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: '600', margin: '0 0 4px 0', fontSize: '0.95rem' }}>{doc.name}</p>
                  <p style={{ fontSize: '0.8rem', color: '#6b7280', margin: 0 }}>{formatSize(doc.size)} · {new Date(doc.uploaded_at).toLocaleDateString()}</p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button onClick={() => handleDownload(doc.id, doc.name)}style={{ padding: '6px 10px', background: '#e0e7ff', color: '#4f46e5', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}title="Download File">↓</button>
                  <button onClick={() => deleteDoc(doc.id)} style={{ padding: '6px 10px', background: '#fee2e2', color: '#dc2626', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* UPLOAD MODAL */}
      {showUpload && (
        <div className="create-overlay">
          <div className="create-modal">
            <div className="create-header">
              <h2>Upload Document</h2>
              <button className="close-button" onClick={() => setShowUpload(false)}>✕</button>
            </div>
            <input type="file" ref={fileInputRef} onChange={(e) => setUploadFile(e.target.files[0])} style={{ display: 'block', marginBottom: '16px' }} />
            
            <div className="field-group">
              <label>Category</label>
              <select value={uploadCat} onChange={(e) => setUploadCat(e.target.value)}>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            
            <div className="field-group">
              <label>Tags</label>
              <input type="text" value={uploadTags} onChange={(e) => setUploadTags(e.target.value)} placeholder="e.g. Q4, draft" />
            </div>

            <div className="create-actions">
              <button className="cancel-button" onClick={() => setShowUpload(false)}>Cancel</button>
              <button className="submit-button" onClick={handleUpload} disabled={isUploading}>
                {isUploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocVault;