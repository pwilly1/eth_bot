import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button, ButtonGroup, Typography, Box, Chip
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';
import { Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel, Checkbox } from '@mui/material';

function HistoricalData() {
  const [historicalData, setHistoricalData] = useState([]);
  const [q, setQ] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [minLiquidity, setMinLiquidity] = useState('');
  const [ownership, setOwnership] = useState(null);
  const [timeline, setTimeline] = useState('today');
  const [startMs, setStartMs] = useState(null);
  const [endMs, setEndMs] = useState(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
  if (minLiquidity) params.set('min_liquidity', minLiquidity);
  if (ownership !== null) params.set('ownership', ownership ? 'true' : 'false');
  if (startMs) params.set('start_ms', String(startMs));
  if (endMs) params.set('end_ms', String(endMs));
      const res = await fetch('/api/historical_data?' + params.toString());
      const data = await res.json();
      // backend may return either a bare array or an object wrapper; normalize to array
      let list = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object') {
        if (Array.isArray(data.historical_data)) list = data.historical_data;
        else if (Array.isArray(data.token_events)) list = data.token_events;
        else if (Array.isArray(data.results)) list = data.results;
        else {
          // try to extract array-ish values
          const vals = Object.values(data).find(v => Array.isArray(v));
          if (Array.isArray(vals)) list = vals;
        }
      }
      setHistoricalData(list);
    } catch (error) {
      console.error('Error fetching historical data:', error);
    }
  };

  useEffect(() => {
    const interval = setInterval(fetchData, 5000);
    fetchData();
    return () => clearInterval(interval);
  }, [q, minLiquidity, ownership, startMs, endMs]);

  // timeline helper
  const applyTimeline = (tl) => {
    setTimeline(tl);
    const now = Date.now();
    let s = null;
    let e = now;
    if (tl === 'today') {
      const d = new Date();
      d.setHours(0,0,0,0);
      s = d.getTime();
    } else if (tl === '24h') {
      s = now - 24 * 60 * 60 * 1000;
    } else if (tl === '7d') {
      s = now - 7 * 24 * 60 * 60 * 1000;
    } else if (tl === '30d') {
      s = now - 30 * 24 * 60 * 60 * 1000;
    } else if (tl === 'custom') {
      // open dialog for custom range
      setCustomOpen(true);
      return;
    }
    setStartMs(s);
    setEndMs(e);
  };

  return (
    <Paper elevation={3} sx={{ p: 3, my: 3 }}>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField label="Search" value={q} onChange={(e) => setQ(e.target.value)} size="small" sx={{ flex: 1 }} />
        <ButtonGroup variant="outlined">
          <Button onClick={() => applyTimeline('today')} color={timeline==='today' ? 'primary' : 'inherit'}>Today</Button>
          <Button onClick={() => applyTimeline('24h')} color={timeline==='24h' ? 'primary' : 'inherit'}>24h</Button>
          <Button onClick={() => applyTimeline('7d')} color={timeline==='7d' ? 'primary' : 'inherit'}>7d</Button>
          <Button onClick={() => applyTimeline('30d')} color={timeline==='30d' ? 'primary' : 'inherit'}>30d</Button>
          <Button onClick={() => applyTimeline('custom')} color={timeline==='custom' ? 'primary' : 'inherit'}>Custom</Button>
        </ButtonGroup>
        <Button variant='outlined' onClick={() => setFiltersOpen(true)}>Filters</Button>
        <Button onClick={() => { setQ(''); setMinLiquidity(''); setOwnership(null); setStartMs(null); setEndMs(null); setTimeline('today'); }}>Reset</Button>
      </Box>
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
            {historicalData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography>No historical data for the selected range.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              historicalData.map((entry, index) => {
                const main_token = (entry.token0 && (entry.token0.symbol || '').toUpperCase() === 'WETH') ? entry.token1 : entry.token0;
                return (
                  <TableRow key={index} hover sx={{ cursor: 'pointer' }} onClick={() => setSelected(entry)}>
                    <TableCell>{new Date(entry.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{main_token?.name || 'Unknown'} ({main_token?.symbol || 'N/A'})</TableCell>
                    <TableCell>{main_token?.address}</TableCell>
                    <TableCell><Chip label={`${Number(entry.liquidity_eth).toFixed(4)} ETH`} size="small" /></TableCell>
                    <TableCell>{entry.honeypot ? 'Yes' : 'No'}</TableCell>
                    <TableCell>{entry.ownership_renounced ? 'Yes' : 'No'}</TableCell>
                  </TableRow>
                );
              })
            )}
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

      <Dialog open={customOpen} onClose={() => setCustomOpen(false)}>
        <DialogTitle>Custom Range</DialogTitle>
        <DialogContent>
          <TextField label="Start Time" type="datetime-local" value={customStart} onChange={(e) => setCustomStart(e.target.value)} InputLabelProps={{ shrink: true }} fullWidth />
          <TextField label="End Time" type="datetime-local" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} InputLabelProps={{ shrink: true }} fullWidth style={{ marginTop: 10 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomOpen(false)}>Cancel</Button>
          <Button onClick={() => {
            // convert to ms
            const s = customStart ? new Date(customStart).getTime() : null;
            const e = customEnd ? new Date(customEnd).getTime() : Date.now();
            setStartMs(s);
            setEndMs(e);
            setCustomOpen(false);
            setTimeline('custom');
          }}>Apply</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default HistoricalData;
