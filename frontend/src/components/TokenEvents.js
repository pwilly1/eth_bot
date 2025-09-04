import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button, Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel, Checkbox
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';

function TokenEvents() {
  const [tokenEvents, setTokenEvents] = useState([]);
  const [q, setQ] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [minLiquidity, setMinLiquidity] = useState('');
  const [ownership, setOwnership] = useState(null);
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
  if (minLiquidity) params.set('min_liquidity', minLiquidity);
  if (ownership !== null) params.set('ownership', ownership ? 'true' : 'false');
      const tokenEventsRes = await fetch('/api/token_events?' + params.toString());
      const tokenEventsData = await tokenEventsRes.json();
      setTokenEvents(tokenEventsData.token_events || []);
    } catch (error) {
      console.error('Error fetching token events:', error);
    }
  };

  useEffect(() => {
    const interval = setInterval(fetchData, 5000);
    fetchData();
    return () => clearInterval(interval);
  }, [q, honeypotOnly]);

  return (
    <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
        <TextField label="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant='outlined' onClick={() => setFiltersOpen(true)}>Filters</Button>
        <Button onClick={() => { setQ(''); setMinLiquidity(''); setOwnership(null); }}>Reset</Button>
      </div>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Token</TableCell>
              <TableCell>Address</TableCell>
              <TableCell>Liquidity (ETH)</TableCell>
              <TableCell>Honeypot</TableCell>
              <TableCell>Ownership</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tokenEvents.map((event, index) => (
              <TableRow key={index} hover style={{ cursor: 'pointer' }} onClick={() => setSelected(event)}>
                <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                <TableCell>{(event.token1 && event.token1.symbol) || (event.token0 && event.token0.symbol) || 'N/A'}</TableCell>
                <TableCell>{event.address}</TableCell>
                <TableCell>{Number(event.liquidity_eth).toFixed(4)}</TableCell>
                <TableCell>{event.honeypot ? 'Yes' : 'No'}</TableCell>
                <TableCell>{event.ownership_renounced ? 'Yes' : 'No'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TokenDetailModal open={!!selected} onClose={() => setSelected(null)} token={selected} />

      <Dialog open={filtersOpen} onClose={() => setFiltersOpen(false)}>
        <DialogTitle>Filters</DialogTitle>
        <DialogContent>
          <TextField label="Min Liquidity (ETH)" value={minLiquidity} onChange={(e) => setMinLiquidity(e.target.value)} fullWidth type="number" />
          <FormControlLabel control={<Checkbox checked={ownership === true} onChange={(e) => setOwnership(e.target.checked ? true : null)} />} label="Ownership Renounced" />
          <FormControlLabel control={<Checkbox checked={ownership === false} onChange={(e) => setOwnership(e.target.checked ? false : null)} />} label="Ownership Not Renounced" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFiltersOpen(false)}>Close</Button>
          <Button onClick={() => { setFiltersOpen(false); fetchData(); }}>Apply</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default TokenEvents;
