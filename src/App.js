import React, { useState, useEffect } from "react";
import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";
import Dashboard from "./Dashboard";
import VotePage from "./VotePage";
import CreateBallot from "./CreateBallot";
import SuggestBallot from "./SuggestBallot";
import AdminSuggestions from "./AdminSuggestions";
import MyVotes from "./MyVotes";
import ProfilePage from "./ProfilePage";
import { ToastProvider, useToast } from "./Toast";
import "./theme.css";
import DocVault from "./DocVault";
import ChatAnalysis from "./ChatAnalysis";
import Meetings from "./Meetings";
import Announcements from "./Announcements";
import FaqChatbot from "./FaqChatbot";
import FinancePage from "./FinancePage";

function AppInner() {
  const toast = useToast();
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('dashboard');
  const [modal, setModal] = useState(null);
  const [showRegister, setShowRegister] = useState(false);
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('theme') || 'light'; } catch (e) { return 'light'; }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) { /* ignore */ }
  }, [theme]);

  const themeToggle = (
    <button
      className="theme-toggle"
      onClick={() => setTheme(t => (t === 'dark' ? 'light' : 'dark'))}
      title="Toggle dark mode"
      aria-label="Toggle dark mode"
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );

  const handleLogin = (userData) => {
    setUser(userData);
    setPage('dashboard');
    setShowRegister(false);
  };

  const handleLogout = async () => {
    await fetch('/api/logout/', { method: 'POST', credentials: 'include' });
    setUser(null);
    setPage('dashboard');
    setModal(null);
  };

  const handleNavigate = (dest) => {
    if (dest === 'create') {
      setModal(user?.is_admin ? 'create' : 'suggest');
    } else if (dest === 'suggestions') {
      setModal('suggestions');
    } else {
      setPage(dest);
    }
  };

  if (!user) {
    if (showRegister) {
      return <>{<RegisterPage onRegister={handleLogin} onBack={() => setShowRegister(false)} />}{themeToggle}</>;
    }
    return <>{<LoginPage onLogin={handleLogin} onRegister={() => setShowRegister(true)} />}{themeToggle}</>;
  }

  return (
    <>
      {page === 'dashboard' && (
        <Dashboard user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'vote' && (
        <VotePage user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'myvotes' && (
        <MyVotes user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'docvault' && (
        <DocVault user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'chatanalysis' && (
        <ChatAnalysis user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'meetings' && (
        <Meetings user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'announcements' && (
        <Announcements user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'finance' && (
        <FinancePage user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {page === 'profile' && (
        <ProfilePage user={user} setUser={setUser} onLogout={handleLogout} onNavigate={handleNavigate} />
      )}
      {modal === 'create' && (
        <CreateBallot
          onCreated={() => {
            setModal(null);
            setPage('dashboard');
            toast.success('Ballot created successfully.');
          }}
          onCancel={() => setModal(null)}
        />
      )}
      {modal === 'suggest' && (
        <SuggestBallot
          onSent={() => {
            setModal(null);
            toast.success('Suggestion sent! It will be published after admin review.');
          }}
          onCancel={() => setModal(null)}
        />
      )}
      {modal === 'suggestions' && (
        <AdminSuggestions onClose={() => setModal(null)} />
      )}
      <FaqChatbot />
      {themeToggle}
    </>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  );
}
