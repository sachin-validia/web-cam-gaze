import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Container, Box, Typography, Button, Paper, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

interface LocationState {
  success: boolean;
  message?: string;
  filesGenerated?: string[];
  quality?: number;
}

function CompletionPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [state, setState] = useState<LocationState>({ success: false });

  useEffect(() => {
    const locationState = location.state as LocationState;
    if (locationState) {
      setState(locationState);
    } else {
      navigate('/');
    }
  }, [location, navigate]);

  const handleRetryCalibration = () => {
    sessionStorage.clear();
    navigate('/');
  };

  if (!state) {
    return (
      <Container maxWidth="sm">
        <Box sx={{ mt: 8, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Paper elevation={3} sx={{ p: 4, width: '100%', textAlign: 'center' }}>
          {state.success ? (
            <>
              <CheckCircleIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
              <Typography component="h1" variant="h4" gutterBottom>
                Calibration Successful!
              </Typography>
              <Typography variant="body1" sx={{ mb: 3 }}>
                {state.message || 'Your gaze calibration has been completed successfully.'}
              </Typography>
              
              {state.quality && (
                <Typography variant="body2" sx={{ mb: 2 }}>
                  Calibration Quality: {(state.quality * 100).toFixed(0)}%
                </Typography>
              )}
              
              {state.filesGenerated && state.filesGenerated.length > 0 && (
                <Box sx={{ mt: 3, mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Files Generated:
                  </Typography>
                  {state.filesGenerated.map((file, index) => (
                    <Typography key={index} variant="body2">
                      {file}
                    </Typography>
                  ))}
                </Box>
              )}
            </>
          ) : (
            <>
              <ErrorIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
              <Typography component="h1" variant="h4" gutterBottom>
                Calibration Failed
              </Typography>
              <Typography variant="body1" sx={{ mb: 3 }}>
                {state.message || 'The calibration process encountered an error.'}
              </Typography>
            </>
          )}

          <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
              variant="contained"
              onClick={handleRetryCalibration}
              color={state.success ? 'secondary' : 'primary'}
            >
              {state.success ? 'New Calibration' : 'Retry Calibration'}
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default CompletionPage;