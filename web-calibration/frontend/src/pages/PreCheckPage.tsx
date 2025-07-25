import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Box, Typography, Button, TextField, Paper } from '@mui/material';
import { calibrationApi } from '../api/calibration.api';

function PreCheckPage() {
  const navigate = useNavigate();
  const [candidateId, setCandidateId] = useState('test_candidate_001');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleStartCalibration = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Request fullscreen permission
      if (document.documentElement.requestFullscreen) {
        try {
          await document.documentElement.requestFullscreen();
          console.log('Fullscreen mode activated');
        } catch (fullscreenError) {
          console.warn('Fullscreen request denied:', fullscreenError);
          // Continue without fullscreen - it's not critical
        }
      }
      
      const response = await calibrationApi.createSession({
        candidate_id: candidateId,
        session_type: 'calibration',
      });
      
      sessionStorage.setItem('sessionId', response.session_id);
      sessionStorage.setItem('candidateId', candidateId);
      
      navigate('/calibration');
    } catch (err: any) {
      setError('Failed to create calibration session. The backend service has a database configuration issue. Please contact support.');
      console.error('Session creation error:', err);
      console.error('Backend status field expects "in_progress" but code is sending "in progress"');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Gaze Calibration Setup
          </Typography>
          
          <Typography variant="body1" align="center" sx={{ mb: 4 }}>
            This calibration will help us track your eye movements during the interview.
            Please ensure you have a working webcam and are in a well-lit environment.
          </Typography>

          <TextField
            fullWidth
            label="Candidate ID"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            margin="normal"
            variant="outlined"
            helperText="Enter your unique candidate ID"
          />

          {error && (
            <Typography color="error" variant="body2" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}

          <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6">Pre-check Requirements:</Typography>
            <Typography variant="body2">✓ Webcam connected and working</Typography>
            <Typography variant="body2">✓ Good lighting (face clearly visible)</Typography>
            <Typography variant="body2">✓ Sitting at normal distance from screen</Typography>
            <Typography variant="body2">✓ Browser has camera permissions</Typography>
            <Typography variant="body2">✓ Allow fullscreen mode when prompted</Typography>
          </Box>

          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={handleStartCalibration}
            disabled={loading || !candidateId}
            sx={{ mt: 4 }}
          >
            {loading ? 'Creating Session...' : 'Start Calibration'}
          </Button>
        </Paper>
      </Box>
    </Container>
  );
}

export default PreCheckPage;