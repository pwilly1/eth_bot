import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper
} from '@mui/material';

function TokenEvents() {
  const [tokenEvents, setTokenEvents] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const tokenEventsRes = await fetch('/api/token_events');
        const tokenEventsData = await tokenEventsRes.json();
        setTokenEvents(tokenEventsData.token_events);
      } catch (error) {
        console.error('Error fetching token events:', error);
      }
    };

    const interval = setInterval(fetchData, 5000);
    fetchData();

    return () => clearInterval(interval);
  }, []);

  return (
    <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Token Address</TableCell>
              <TableCell>Liquidity (ETH)</TableCell>
              <TableCell>Honeypot</TableCell>
              <TableCell>Ownership Renounced</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tokenEvents.slice().reverse().map((event, index) => (
              <TableRow key={index}>
                <TableCell>{new Date(event.timestamp * 1000).toLocaleString()}</TableCell>
                <TableCell>{event.address}</TableCell>
                <TableCell>{event.liquidity_eth.toFixed(4)}</TableCell>
                <TableCell>{event.honeypot ? 'Yes' : 'No'}</TableCell>
                <TableCell>{event.ownership_renounced ? 'Yes' : 'No'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

export default TokenEvents;
