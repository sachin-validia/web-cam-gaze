import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Stepper, Step, StepLabel, Container } from '@mui/material';
import ScreenSetup from '../components/calibration/ScreenSetup';
import CameraCheck from '../components/calibration/CameraCheck';
import CalibrationTargets from '../components/calibration/CalibrationTargets';
import { calibrationApi } from '../api/calibration.api';
import { CalibrationSession, ScreenInfo } from '../types/calibration.types';

const steps = ['Screen Setup', 'Camera Check', 'Calibration'];

function CalibrationPage() {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [session, setSession] = useState<CalibrationSession>({
    sessionId: '',
    candidateId: '',
    status: 'screen_setup',
  });

  useEffect(() => {
    const sessionId = sessionStorage.getItem('sessionId');
    const candidateId = sessionStorage.getItem('candidateId');
    
    if (!sessionId || !candidateId) {
      navigate('/');
      return;
    }
    
    setSession({
      sessionId,
      candidateId,
      status: 'screen_setup',
    });
  }, [navigate]);

  const handleScreenSetupComplete = async (screenInfo: ScreenInfo) => {
    try {
      await calibrationApi.saveScreenInfo({
        session_id: session.sessionId,
        screen_width: screenInfo.width,
        screen_height: screenInfo.height,
        dpi: screenInfo.dpi,
      });
      
      setSession(prev => ({ ...prev, screenInfo, status: 'camera_check' }));
      setActiveStep(1);
    } catch (error) {
      console.error('Failed to save screen info:', error);
    }
  };

  const handleCameraCheckComplete = async () => {
    try {
      await calibrationApi.startCalibration({
        session_id: session.sessionId,
        calibration_type: 'standard',
      });
      
      setSession(prev => ({ ...prev, status: 'calibrating' }));
      setActiveStep(2);
    } catch (error) {
      console.error('Failed to start calibration:', error);
    }
  };

  const handleCalibrationComplete = async (result: { success: boolean; message: string }) => {
    try {
      const response = await calibrationApi.completeCalibration({
        session_id: session.sessionId,
      });
      
      navigate('/completion', {
        state: {
          success: response.success,
          message: response.message,
          filesGenerated: response.files_generated,
          quality: response.calibration_quality,
        },
      });
    } catch (error) {
      console.error('Failed to complete calibration:', error);
      navigate('/completion', {
        state: {
          success: false,
          message: 'Failed to complete calibration. Please try again.',
        },
      });
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ width: '100%', mt: 4 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        <Box sx={{ mt: 4 }}>
          {activeStep === 0 && (
            <ScreenSetup onComplete={handleScreenSetupComplete} />
          )}
          
          {activeStep === 1 && (
            <CameraCheck onComplete={handleCameraCheckComplete} />
          )}
          
          {activeStep === 2 && session.screenInfo && (
            <CalibrationTargets
              sessionId={session.sessionId}
              screenInfo={session.screenInfo}
              onComplete={handleCalibrationComplete}
            />
          )}
        </Box>
      </Box>
    </Container>
  );
}

export default CalibrationPage;