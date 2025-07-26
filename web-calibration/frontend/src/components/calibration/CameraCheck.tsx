import { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Box, Paper, Typography, Button, Alert, CircularProgress } from '@mui/material';
import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';

interface CameraCheckProps {
  onComplete: () => void;
}

function CameraCheck({ onComplete }: CameraCheckProps) {
  const webcamRef = useRef<Webcam>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const handleUserMedia = useCallback(() => {
    setHasPermission(true);
    setIsLoading(false);
    setError('');
  }, []);

  const handleUserMediaError = useCallback((error: string | DOMException) => {
    console.error('Camera access error:', error);
    setHasPermission(false);
    setIsLoading(false);
    setError('Camera access denied. Please allow camera permissions and refresh.');
  }, []);

  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: 'user',
  };

  const handleContinue = () => {
    if (hasPermission) {
      onComplete();
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Camera Check
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3 }}>
        Please allow camera access when prompted. Make sure your face is clearly visible and well-lit.
      </Typography>

      <Box sx={{ position: 'relative', mb: 3 }}>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 480, bgcolor: 'grey.200' }}>
            <CircularProgress />
          </Box>
        )}
        
        {!hasPermission && !isLoading && (
          <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: 480, bgcolor: 'grey.200' }}>
            <VideocamOffIcon sx={{ fontSize: 80, color: 'grey.500', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">Camera Access Required</Typography>
          </Box>
        )}
        
        <Box sx={{ display: hasPermission ? 'block' : 'none', backgroundColor: 'black', borderRadius: 1, overflow: 'hidden' }}>
          <Webcam
            ref={webcamRef}
            audio={false}
            videoConstraints={videoConstraints}
            onUserMedia={handleUserMedia}
            onUserMediaError={handleUserMediaError}
            style={{ width: '100%', height: 'auto', display: 'block' }}
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {hasPermission && (
        <Alert severity="success" sx={{ mb: 3 }} icon={<VideocamIcon />}>
          Camera connected successfully! Make sure:
          <ul style={{ marginTop: 8, marginBottom: 0 }}>
            <li>Your face is clearly visible</li>
            <li>The room is well-lit</li>
            <li>You're at a comfortable distance from the screen</li>
          </ul>
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          size="large"
          onClick={handleContinue}
          disabled={!hasPermission}
          startIcon={hasPermission ? <VideocamIcon /> : <VideocamOffIcon />}
        >
          {hasPermission ? 'Continue to Calibration' : 'Waiting for Camera Access'}
        </Button>
      </Box>
    </Paper>
  );
}

export default CameraCheck;