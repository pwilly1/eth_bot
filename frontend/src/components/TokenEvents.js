import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button, Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel, Checkbox, Typography, Box, Chip
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';

function TokenEvents() {
  const [tokenEvents, setTokenEvents] = useState([]);
  const [q, setQ] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [minLiquidity, setMinLiquidity] = useState('');
  const [ownership, setOwnership] = useState(null);
  const [honeypot, setHoneypot] = useState(null);
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
  if (minLiquidity) params.set('min_liquidity', minLiquidity);
  if (ownership !== null) params.set('ownership', ownership ? 'true' : 'false');
  if (honeypot !== null) params.set('honeypot', honeypot ? 'true' : 'false');
  // startTime/endTime are ISO-local strings from <input type="datetime-local">; convert to ms
  if (startTime) {
    const sMs = new Date(startTime).getTime();
    if (!isNaN(sMs)) params.set('start_ms', String(sMs));
  }
  if (endTime) {
    const eMs = new Date(endTime).getTime();
    if (!isNaN(eMs)) params.set('end_ms', String(eMs));
  }
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
  }, [q, minLiquidity, ownership, honeypot, startTime, endTime]);

  return (
    <Paper elevation={3} sx={{ p: 3, my: 3 }}>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField label="Search" value={q} onChange={(e) => setQ(e.target.value)} size="small" sx={{ flex: 1 }} />
        <Button variant='outlined' onClick={() => setFiltersOpen(true)}>Filters</Button>
        <Button onClick={() => { setQ(''); setMinLiquidity(''); setOwnership(null); setHoneypot(null); setStartTime(''); setEndTime(''); }}>Reset</Button>
      </Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>Today's Activity</Typography>
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
            {tokenEvents.map((event, index) => {
              const t0 = event.token0 || {};
              const t1 = event.token1 || {};
              // Prefer the non-WETH token as the displayed token
              const isT0Weth = (t0.symbol || '').toUpperCase() === 'WETH';
              const isT1Weth = (t1.symbol || '').toUpperCase() === 'WETH';
              let mainToken = t0;
              if (isT0Weth && !isT1Weth) mainToken = t1;
              else if (isT1Weth && !isT0Weth) mainToken = t0;
              else if (t1 && (t1.symbol || t1.name)) mainToken = t1; // fallback prefer token1 if available

              const displayName = mainToken.name || mainToken.symbol || 'N/A';

              return (
                <TableRow key={index} hover style={{ cursor: 'pointer' }} onClick={() => setSelected(event)}>
                  <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{displayName}{mainToken.symbol ? ` (${mainToken.symbol})` : ''}</TableCell>
                    <TableCell>{event.address}</TableCell>
                    <TableCell><Chip label={`${Number(event.liquidity_eth).toFixed(4)} ETH`} size="small" /></TableCell>
                  <TableCell>{event.honeypot ? 'Yes' : 'No'}</TableCell>
                  <TableCell>{event.ownership_renounced ? 'Yes' : 'No'}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <TokenDetailModal open={!!selected} onClose={() => setSelected(null)} token={selected} />

      <Dialog open={filtersOpen} onClose={() => setFiltersOpen(false)}>
        <DialogTitle>Filters</DialogTitle>
        <DialogContent>
          <TextField label="Min Liquidity (ETH)" value={minLiquidity} onChange={(e) => setMinLiquidity(e.target.value)} fullWidth type="number" />
          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <FormControlLabel control={<Checkbox checked={ownership === true} onChange={(e) => setOwnership(e.target.checked ? true : null)} />} label="Ownership Renounced" />
            <FormControlLabel control={<Checkbox checked={ownership === false} onChange={(e) => setOwnership(e.target.checked ? false : null)} />} label="Ownership Not Renounced" />
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '10px', alignItems: 'center' }}>
            <FormControlLabel control={<Checkbox checked={honeypot === true} onChange={(e) => setHoneypot(e.target.checked ? true : null)} />} label="Honeypot" />
            <FormControlLabel control={<Checkbox checked={honeypot === false} onChange={(e) => setHoneypot(e.target.checked ? false : null)} />} label="Not Honeypot" />
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <TextField label="Start Time" type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} InputLabelProps={{ shrink: true }} />
            <TextField label="End Time" type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} InputLabelProps={{ shrink: true }} />
          </div>
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
