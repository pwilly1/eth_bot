import React, { useState, useEffect } from 'react';
import { Paper, TextField, Button, List, ListItem, ListItemText, Typography } from '@mui/material';

function WatchlistManager() {
  const API_BASE = process.env.REACT_APP_API_BASE || '';
  const [watchlist, setWatchlist] = useState([]);
  const [addr, setAddr] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/watchlist`);
      const data = await res.json();
      setWatchlist(data.watchlist || []);
    } catch (e) {
      console.error('Failed to load watchlist', e);
    }
  };

  useEffect(() => { fetchWatchlist(); }, []);

  const addAddress = async () => {
    if (!addr) return;
    setLoading(true);
    try {
  const res = await fetch(`${API_BASE}/api/watchlist/add?address=${encodeURIComponent(addr)}`, { method: 'POST' });
      const data = await res.json();
      setWatchlist(data.watchlist || []);
      setAddr('');
    } catch (e) {
      console.error('Add failed', e);
    } finally { setLoading(false); }
  };

  const removeAddress = async (a) => {
    setLoading(true);
    try {
  const res = await fetch(`${API_BASE}/api/watchlist/remove?address=${encodeURIComponent(a)}`, { method: 'POST' });
      const data = await res.json();
      setWatchlist(data.watchlist || []);
    } catch (e) {
      console.error('Remove failed', e);
    } finally { setLoading(false); }
  };

  return (
    <Paper elevation={3} style={{ padding: 20 }}>
      <Typography variant="h6" gutterBottom>Watchlist</Typography>
      <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
        <TextField label="Address" value={addr} onChange={(e) => setAddr(e.target.value)} fullWidth />
        <Button variant="contained" onClick={addAddress} disabled={loading}>Add</Button>
      </div>
      <List>
        {watchlist.map((w) => (
          <ListItem key={w}>
            <ListItemText primary={w} />
            <Button size="small" color="error" onClick={() => removeAddress(w)}>Remove</Button>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}

export default WatchlistManager;
