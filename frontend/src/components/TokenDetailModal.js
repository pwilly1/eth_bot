import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from '@mui/material';

function TokenDetailModal({ open, onClose, token }) {
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!open || !token) return;

    const addr = token.address || token.token0?.address || token.token1?.address;
    if (!addr) return;

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/token/${addr}`);
        if (!res.ok) throw new Error('Token detail not found');
        const data = await res.json();
        if (!cancelled) setDetail(data);
      } catch (e) {
        console.error('Error loading token detail', e);
      }
    })();

    return () => { cancelled = true; setDetail(null); };
  }, [open, token]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Token Details</DialogTitle>
      <DialogContent>
        {detail ? (
          <div>
            <Typography variant="subtitle1">Address: {detail.address}</Typography>
            <Typography variant="body2">Pair: {detail.pair_address}</Typography>
            <Typography variant="body2">Liquidity (ETH): {detail.liquidity_eth}</Typography>
            <Typography variant="body2">Honeypot: {detail.honeypot ? 'Yes' : 'No'}</Typography>
            <Typography variant="body2">Ownership Renounced: {detail.ownership_renounced ? 'Yes' : 'No'}</Typography>
            <Typography variant="body2">Token0: {detail.token0.name} ({detail.token0.symbol})</Typography>
            <Typography variant="body2">Token1: {detail.token1.name} ({detail.token1.symbol})</Typography>
            <pre style={{ marginTop: 10, maxHeight: 200, overflow: 'auto' }}>{JSON.stringify(detail.raw, null, 2)}</pre>
          </div>
        ) : (
          <Typography>Loading...</Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

export default TokenDetailModal;
