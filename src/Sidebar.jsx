import React from "react";

// Single source of truth for the left navigation.
// Every page renders <Sidebar active="..." /> so the menu never drifts
// between pages (previously each page hardcoded its own list).
const NAV_ITEMS = [
  { key: "dashboard", icon: "📊", label: "Dashboard" },
  { key: "vote", icon: "🗳️", label: "Ballots" },
  { key: "myvotes", icon: "🧾", label: "My Votes" },
  { key: "docvault", icon: "📁", label: "Documents" },
  { key: "chatanalysis", icon: "💬", label: "Chat Analysis" },
  { key: "meetings", icon: "📅", label: "Meetings" },
  { key: "announcements", icon: "📣", label: "Announcements" },
  { key: "finance", icon: "💰", label: "Finance" },
];

export default function Sidebar({ user, active, onLogout, onNavigate, children }) {
  const name = user?.display_name || user?.username || user?.email || "?";
  const initial = name[0].toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-text">Company Portal</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            className={"nav-item" + (active === item.key ? " active" : "")}
            onClick={() => onNavigate(item.key)}
          >
            <span>{item.icon}</span> {item.label}
          </button>
        ))}

        {user?.is_admin && (
          <button
            className={"nav-item" + (active === "suggestions" ? " active" : "")}
            onClick={() => onNavigate("suggestions")}
          >
            <span>💡</span> Suggestions
          </button>
        )}

        <button
          className={"nav-item" + (active === "profile" ? " active" : "")}
          onClick={() => onNavigate("profile")}
        >
          <span>👤</span> Profile
        </button>
      </nav>

      {children}

      <div className="sidebar-user">
        {user?.profile_picture ? (
          <img src={user.profile_picture} alt="avatar" className="user-avatar-img" />
        ) : (
          <div className="user-avatar">{initial}</div>
        )}
        <div className="user-info">
          <span className="user-name">{name}</span>
          <button className="logout-link" onClick={onLogout}>Sign Out</button>
        </div>
      </div>
    </aside>
  );
}
