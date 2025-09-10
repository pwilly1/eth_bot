import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button } from '@mui/material';

function Auth({ apiBase = '', onLogin }) {
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const openDialog = () => setOpen(true);
  const closeDialog = () => setOpen(false);

  const doLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const txt = await res.text();
        setError(`Login failed: ${res.status} ${txt}`);
        return;
      }
      const data = await res.json();
      const token = data.access_token;
      if (token) {
        localStorage.setItem('ethbot_token', token);
        // fetch profile
        try {
          const profileRes = await fetch(`${apiBase}/api/me`, { headers: { Authorization: `Bearer ${token}` } });
          if (profileRes.ok) {
            const profile = await profileRes.json();
            onLogin && onLogin(token, profile.username);
          } else {
            onLogin && onLogin(token, null);
          }
        } catch (e) {
          onLogin && onLogin(token, null);
        }
        closeDialog();
      } else {
        setError('No token received');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const doRegister = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const txt = await res.text();
        setError(`Register failed: ${res.status} ${txt}`);
        return;
      }
      // after register, login automatically
      await doLogin();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const doLogout = () => {
    localStorage.removeItem('ethbot_token');
    onLogin && onLogin(null, null);
    closeDialog();
  };

  return (
    <>
      <Button variant="outlined" color="inherit" onClick={openDialog}>Login/Register</Button>
      <Dialog open={open} onClose={closeDialog}>
        <DialogTitle>Login or Register</DialogTitle>
        <DialogContent>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 320 }}>
            <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
            <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            {error && <div style={{ color: 'salmon' }}>{error}</div>}
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={doLogout} color="secondary">Logout</Button>
          <Button onClick={doRegister} disabled={loading}>Register</Button>
          <Button onClick={doLogin} variant="contained" disabled={loading}>Login</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default Auth;
