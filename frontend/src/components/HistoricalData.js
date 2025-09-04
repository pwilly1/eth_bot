import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';
import { Dialog, DialogTitle, DialogContent, DialogActions, FormControlLabel, Checkbox } from '@mui/material';

function HistoricalData() {
  const [historicalData, setHistoricalData] = useState([]);
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
      const res = await fetch('/api/historical_data?' + params.toString());
      const data = await res.json();
      setHistoricalData(data || []);
    } catch (error) {
      console.error('Error fetching historical data:', error);
    }
  };

  useEffect(() => {
    const interval = setInterval(fetchData, 5000);
    fetchData();
    return () => clearInterval(interval);
  }, [q, minLiquidity, ownership]);

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
            {historicalData.map((entry, index) => {
              const main_token = (entry.token0 && entry.token0.symbol === 'WETH') ? entry.token1 : entry.token0;
              return (
                <TableRow key={index} hover style={{ cursor: 'pointer' }} onClick={() => setSelected(entry)}>
                  <TableCell>{new Date(entry.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{main_token?.name || 'Unknown'} ({main_token?.symbol || 'N/A'})</TableCell>
                  <TableCell>{main_token?.address}</TableCell>
                  <TableCell>{Number(entry.liquidity_eth).toFixed(4)}</TableCell>
                  <TableCell>{entry.honeypot ? 'Yes' : 'No'}</TableCell>
                  <TableCell>{entry.ownership_renounced ? 'Yes' : 'No'}</TableCell>
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

export default HistoricalData;
