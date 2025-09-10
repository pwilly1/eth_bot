import React, { useState, useEffect } from 'react';
import { Paper, TextField, Button, List, ListItem, ListItemText, Typography } from '@mui/material';

function WatchlistManager({ token = null }) {
  const API_BASE = process.env.REACT_APP_BACKEND_URL || '';
  const [watchlist, setWatchlist] = useState([]);
  const [addr, setAddr] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchWatchlist = async () => {
    setError(null);
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_BASE}/api/watchlist`, { headers });
      const ct = res.headers.get('content-type') || '';
      if (!res.ok) {
        const txt = await res.text();
        console.error('Failed to load watchlist:', res.status, txt);
        setError(`Server error ${res.status}`);
        setWatchlist([]);
        return;
      }
      if (!ct.includes('application/json')) {
        const txt = await res.text();
        console.error('Expected JSON but got:', txt.substring(0, 400));
        setError('Unexpected non-JSON response from API (check REACT_APP_API_BASE)');
        setWatchlist([]);
        return;
      }
      const data = await res.json();
      setWatchlist(data.watchlist || []);
    } catch (e) {
      console.error('Failed to load watchlist', e);
      setError(String(e));
      setWatchlist([]);
    }
  };

  useEffect(() => { fetchWatchlist(); }, [token]);

  const addAddress = async () => {
    if (!addr) return;
    setError(null);
    setLoading(true);
    try {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api/watchlist/add?address=${encodeURIComponent(addr)}`, { method: 'POST', headers });
      const ct = res.headers.get('content-type') || '';
      if (!res.ok) {
        const txt = await res.text();
        console.error('Add failed:', res.status, txt);
        setError(`Server error ${res.status}`);
        return;
      }
      if (!ct.includes('application/json')) {
        const txt = await res.text();
        console.error('Add returned non-JSON:', txt.substring(0,400));
        setError('Unexpected non-JSON response from API');
        return;
      }
      const data = await res.json();
      setWatchlist(data.watchlist || []);
      setAddr('');
    } catch (e) {
      console.error('Add failed', e);
      setError(String(e));
    } finally { setLoading(false); }
  };

  const removeAddress = async (a) => {
    setError(null);
    setLoading(true);
    try {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api/watchlist/remove?address=${encodeURIComponent(a)}`, { method: 'POST', headers });
      const ct = res.headers.get('content-type') || '';
      if (!res.ok) {
        const txt = await res.text();
        console.error('Remove failed:', res.status, txt);
        setError(`Server error ${res.status}`);
        return;
      }
      if (!ct.includes('application/json')) {
        const txt = await res.text();
        console.error('Remove returned non-JSON:', txt.substring(0,400));
        setError('Unexpected non-JSON response from API');
        return;
      }
      const data = await res.json();
      setWatchlist(data.watchlist || []);
    } catch (e) {
      console.error('Remove failed', e);
      setError(String(e));
    } finally { setLoading(false); }
  };

  return (
    <Paper elevation={3} style={{ padding: 20 }}>
      <Typography variant="h6" gutterBottom>Watchlist</Typography>
      <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
        <TextField label="Address" value={addr} onChange={(e) => setAddr(e.target.value)} fullWidth />
        <Button variant="contained" onClick={addAddress} disabled={loading}>Add</Button>
      </div>
      {error ? (
        <Typography color="error" sx={{ mt: 1 }}>{error}</Typography>
      ) : (
        <List>
          {watchlist.map((w) => (
            <ListItem key={w}>
              <ListItemText primary={w} />
              <Button size="small" color="error" onClick={() => removeAddress(w)}>Remove</Button>
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}

export default WatchlistManager;
