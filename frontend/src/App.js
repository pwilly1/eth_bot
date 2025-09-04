import React, { useState, useEffect } from 'react';
import {
  AppBar, Toolbar, Typography, Container, Tabs, Tab, Box, CssBaseline
} from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import TokenEvents from './components/TokenEvents';
import WalletAlerts from './components/WalletAlerts';
import HistoricalData from './components/HistoricalData';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
});

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function App() {
  const [status, setStatus] = useState('Loading...');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        setStatus(statusData.status);
      } catch (error) {
        console.error('Error fetching status:', error);
        setStatus('Error fetching status.');
      }
    };

    const interval = setInterval(fetchStatus, 5000);
    fetchStatus();

    return () => clearInterval(interval);
  }, []);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            ETH Bot
          </Typography>
          <Typography variant="h6">Status: {status}</Typography>
        </Toolbar>
      </AppBar>
      <Container>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="basic tabs example">
            <Tab label="Token Events" />
            <Tab label="Wallet Alerts" />
            <Tab label="Historical Data" />
          </Tabs>
        </Box>
        <TabPanel value={tabValue} index={0}>
          <TokenEvents />
        </TabPanel>
        <TabPanel value={tabValue} index={1}>
          <WalletAlerts />
        </TabPanel>
        <TabPanel value={tabValue} index={2}>
          <HistoricalData />
        </TabPanel>
      </Container>
    </ThemeProvider>
  );
}

export default App;
