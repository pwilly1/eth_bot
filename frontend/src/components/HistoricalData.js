import React, { useState, useEffect } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper
} from '@mui/material';

function HistoricalData() {
  const [historicalData, setHistoricalData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const historicalDataRes = await fetch('/historical_data');
        const historicalData = await historicalDataRes.json();
        if (Array.isArray(historicalData)) {
          setHistoricalData(historicalData);
        }
      } catch (error) {
        console.error('Error fetching historical data:', error);
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
              <TableCell>Token Name</TableCell>
              <TableCell>Token Address</TableCell>
              <TableCell>Liquidity (ETH)</TableCell>
              <TableCell>Honeypot</TableCell>
              <TableCell>Ownership Renounced</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {historicalData.slice().reverse().map((entry, index) => {
              const main_token = entry.token0.symbol === 'WETH' ? entry.token1 : entry.token0;
              return (
                <TableRow key={index}>
                  <TableCell>{new Date(entry.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{main_token.name} ({main_token.symbol})</TableCell>
                  <TableCell>{main_token.address}</TableCell>
                  <TableCell>{entry.liquidity_eth.toFixed(4)}</TableCell>
                  <TableCell>{entry.honeypot ? 'Yes' : 'No'}</TableCell>
                  <TableCell>{entry.ownership_renounced ? 'Yes' : 'No'}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

export default HistoricalData;
