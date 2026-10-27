import React, { useState, useEffect } from 'react';
import './RegisterPage.css';

const API_URL = '/api';
const GOOGLE_CLIENT_ID = '816595047774-00srjbskmn4lkfnr9osl0873utg66h0g.apps.googleusercontent.com';

const RegisterPage = ({ onRegister, onBack }) => {
  const [form, setForm] = useState({ email: '', password: '', password2: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
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
        document.getElementById('google-btn-register'),
        { theme: 'outline', size: 'large', width: 320, text: 'signup_with' }
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
        onRegister(data.user);
      } else {
        setError(data.error || 'Google sign-up failed.');
      }
    } catch (err) {
      setError('Could not connect to server.');
    }
  };

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.password2) { setError('Passwords do not match.'); return; }
    if (form.password.length < 6) { setError('Password must be at least 6 characters.'); return; }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data === 'object' ? Object.values(data).flat().join(' ') : 'Registration failed.');
        return;
      }
      setSuccess('Account created! Signing you in...');
      setTimeout(() => onRegister(data.user), 1000);
    } catch (err) {
      setError('Could not connect to server.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-wrapper">
      <div className="register-form">
        <div className="register-header">
          <button className="back-btn" onClick={onBack}>← Back</button>
          <h2>Create Account</h2>
          <p className="register-sub">Sign up for free</p>
        </div>

        {error && <div className="message-box error">{error}</div>}
        {success && <div className="message-box success">{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Email Address</label>
            <input name="email" type="email" placeholder="example@mail.com" value={form.email} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Password</label>
            <input name="password" type="password" placeholder="At least 6 characters" value={form.password} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Confirm Password</label>
            <input name="password2" type="password" placeholder="Re-enter your password" value={form.password2} onChange={handleChange} required />
          </div>
          <button type="submit" className="register-button" disabled={isLoading}>
            {isLoading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="divider"><span>or</span></div>

        <div id="google-btn-register" className="google-btn-wrap"></div>

        <p className="login-link">
          Already have an account? <button onClick={onBack}>Sign In</button>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
