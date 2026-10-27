import React, { useState, useEffect } from 'react';
import './LoginPage.css';

const API_URL = '/api';
const GOOGLE_CLIENT_ID = '816595047774-00srjbskmn4lkfnr9osl0873utg66h0g.apps.googleusercontent.com';

const LoginPage = ({ onLogin, onRegister }) => {
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Load Google Identity Services script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-btn'),
        { theme: 'outline', size: 'large', width: 320, text: 'signin_with' }
      );
    };
    document.body.appendChild(script);
  }, []);

  const handleGoogleResponse = async (response) => {
    try {
      const res = await fetch(`${API_URL}/auth/google/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ token: response.credential }),
      });
      const data = await res.json();
      if (res.ok) {
        onLogin(data.user);
      } else {
        setMessage(data.error || 'Google sign-in failed.');
      }
    } catch (err) {
      setMessage('Could not connect to server.');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    try {
      const response = await fetch(`${API_URL}/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(credentials),
      });
      const data = await response.json();
      if (response.ok) {
        onLogin(data.user);
      } else {
        setMessage(data.error || 'Login failed.');
      }
    } catch (error) {
      setMessage('Could not connect to server. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="login-form" onSubmit={handleFormSubmit}>
        <h2>Sign In</h2>
        <p className="login-sub">Sign in to your account</p>

        {message && <div className="message-box error">{message}</div>}

        <div className="input-group">
          <label>Email Address</label>
          <input name="email" type="email" placeholder="example@mail.com" value={credentials.email} onChange={handleInputChange} required />
        </div>
        <div className="input-group">
          <label>Password</label>
          <input name="password" type="password" placeholder="Enter your password" value={credentials.password} onChange={handleInputChange} required />
        </div>
        <button type="submit" className="login-button" disabled={isLoading}>
          {isLoading ? 'Signing In...' : 'Sign In'}
        </button>

        <div className="divider"><span>or</span></div>

        <div id="google-btn" className="google-btn-wrap"></div>

        <p className="register-link">
          Don't have an account? <button type="button" onClick={onRegister}>Sign Up</button>
        </p>
      </form>
    </div>
  );
};

export default LoginPage;
