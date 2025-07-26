import { useState, useEffect } from 'react';
import { Box, Paper, Typography, TextField, Button, Grid, Alert } from '@mui/material';
import { ScreenInfo } from '../../types/calibration.types';

interface ScreenSetupProps {
  onComplete: (screenInfo: ScreenInfo) => void;
}

function ScreenSetup({ onComplete }: ScreenSetupProps) {
  const [screenInfo, setScreenInfo] = useState<ScreenInfo>({
    width: window.screen.width,
    height: window.screen.height,
    dpi: 96,
  });
  const [autoDetected, setAutoDetected] = useState(true);

  useEffect(() => {
    const detectDPI = () => {
      const div = document.createElement('div');
      div.style.width = '1in';
      div.style.position = 'absolute';
      div.style.left = '-9999px';
      document.body.appendChild(div);
      const dpi = div.offsetWidth;
      document.body.removeChild(div);
      return dpi || 96;
    };

    const detectedDPI = detectDPI();
    setScreenInfo(prev => ({
      ...prev,
      width: window.screen.width,
      height: window.screen.height,
      dpi: detectedDPI,
      physicalWidth: (window.screen.width / detectedDPI) * 25.4,
      physicalHeight: (window.screen.height / detectedDPI) * 25.4,
    }));
  }, []);

  const handleManualInput = (field: keyof ScreenInfo, value: string) => {
    const numValue = parseInt(value, 10);
    if (!isNaN(numValue) && numValue > 0) {
      setScreenInfo(prev => {
        const updated = { ...prev, [field]: numValue };
        if (field === 'width' || field === 'height' || field === 'dpi') {
          updated.physicalWidth = (updated.width / updated.dpi) * 25.4;
          updated.physicalHeight = (updated.height / updated.dpi) * 25.4;
        }
        return updated;
      });
      setAutoDetected(false);
    }
  };

  const handleSubmit = () => {
    if (screenInfo.width > 0 && screenInfo.height > 0 && screenInfo.dpi > 0) {
      onComplete(screenInfo);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Screen Setup
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3 }}>
        We need to know your screen dimensions for accurate gaze calibration.
        {autoDetected && ' We\'ve auto-detected your screen settings.'}
      </Typography>

      {autoDetected && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Screen dimensions auto-detected. Click continue if they look correct.
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} sm={4}>
          <TextField
            fullWidth
            label="Width (pixels)"
            type="number"
            value={screenInfo.width}
            onChange={(e) => handleManualInput('width', e.target.value)}
            InputProps={{ inputProps: { min: 800, max: 7680 } }}
          />
        </Grid>
        
        <Grid item xs={12} sm={4}>
          <TextField
            fullWidth
            label="Height (pixels)"
            type="number"
            value={screenInfo.height}
            onChange={(e) => handleManualInput('height', e.target.value)}
            InputProps={{ inputProps: { min: 600, max: 4320 } }}
          />
        </Grid>
        
        <Grid item xs={12} sm={4}>
          <TextField
            fullWidth
            label="DPI"
            type="number"
            value={screenInfo.dpi}
            onChange={(e) => handleManualInput('dpi', e.target.value)}
            InputProps={{ inputProps: { min: 72, max: 300 } }}
          />
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Physical dimensions: {screenInfo.physicalWidth?.toFixed(0)}mm × {screenInfo.physicalHeight?.toFixed(0)}mm
          ({(screenInfo.physicalWidth! / 25.4).toFixed(1)}" × {(screenInfo.physicalHeight! / 25.4).toFixed(1)}")
        </Typography>
      </Box>

      <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={!screenInfo.width || !screenInfo.height || !screenInfo.dpi}
        >
          Continue
        </Button>
      </Box>
    </Paper>
  );
}

export default ScreenSetup;