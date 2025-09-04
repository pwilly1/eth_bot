import React, { useState, useEffect } from 'react';
import { List, ListItem, ListItemText, Paper } from '@mui/material';

function WalletAlerts() {
  const [walletAlerts, setWalletAlerts] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const walletAlertsRes = await fetch('/api/wallet_alerts');
        const walletAlertsData = await walletAlertsRes.json();
        setWalletAlerts(walletAlertsData.wallet_alerts);
      } catch (error) {
        console.error('Error fetching wallet alerts:', error);
      }
    };

    const interval = setInterval(fetchData, 5000);
    fetchData();

    return () => clearInterval(interval);
  }, []);

  return (
    <Paper elevation={3} style={{ padding: '20px', margin: '20px 0' }}>
      <List>
        {walletAlerts.map((alert, index) => (
          <ListItem key={index}>
            <ListItemText primary={alert} />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}

export default WalletAlerts;
