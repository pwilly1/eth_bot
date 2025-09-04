import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';

function HistoricalData() {
  const [historicalData, setHistoricalData] = useState([]);
  const [q, setQ] = useState('');
  const [honeypotOnly, setHoneypotOnly] = useState(false);
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (honeypotOnly) params.set('honeypot', 'true');
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
  }, [q, honeypotOnly]);

  return (
    <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
        <TextField label="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant={honeypotOnly ? 'contained' : 'outlined'} onClick={() => setHoneypotOnly(!honeypotOnly)}>
          Honeypots Only
        </Button>
        <Button onClick={() => { setQ(''); setHoneypotOnly(false); }}>Reset</Button>
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
    </Paper>
  );
}

export default HistoricalData;
