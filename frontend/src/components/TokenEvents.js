import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField, Button
} from '@mui/material';
import TokenDetailModal from './TokenDetailModal';

function TokenEvents() {
  const [tokenEvents, setTokenEvents] = useState([]);
  const [q, setQ] = useState('');
  const [honeypotOnly, setHoneypotOnly] = useState(false);
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (honeypotOnly) params.set('honeypot', 'true');
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
    </Paper>
  );
}

export default TokenEvents;
