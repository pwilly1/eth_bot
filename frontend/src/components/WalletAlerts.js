import React, { useState, useEffect } from 'react';
import { List, ListItem, ListItemText, Paper, Typography, Box } from '@mui/material';

function WalletAlerts() {
  const [walletAlerts, setWalletAlerts] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const walletAlertsRes = await fetch('/api/wallet_alerts');
        const walletAlertsData = await walletAlertsRes.json();
        setWalletAlerts(walletAlertsData.wallet_alerts || []);
      } catch (error) {
        console.error('Error fetching wallet alerts:', error);
      }
    };

    const interval = setInterval(fetchData, 5000);
    fetchData();

    return () => clearInterval(interval);
  }, []);

  return (
    <Paper elevation={3} sx={{ p: 3, my: 3 }}>
      <Box>
        <Typography variant="h6" gutterBottom>Wallet Alerts</Typography>
        {walletAlerts.length === 0 ? (
          <Typography>No wallet alerts yet.</Typography>
        ) : (
          <List>
            {walletAlerts.map((alert, index) => (
              <ListItem key={index}>
                <ListItemText primary={alert} />
              </ListItem>
            ))}
          </List>
        )}
      </Box>
    </Paper>
  );
}

export default WalletAlerts;
