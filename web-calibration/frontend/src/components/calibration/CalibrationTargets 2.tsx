import { useState, useEffect, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Box, Typography, LinearProgress } from '@mui/material';
import { calibrationApi } from '../../api/calibration.api';
import { ScreenInfo, CalibrationTarget } from '../../types/calibration.types';

interface CalibrationTargetsProps {
  sessionId: string;
  screenInfo: ScreenInfo;
  onComplete: (result: { success: boolean; message: string }) => void;
}

const FRAMES_PER_TARGET = 30;
const CAPTURE_INTERVAL = 100; // milliseconds

function CalibrationTargets({ sessionId, screenInfo, onComplete }: CalibrationTargetsProps) {
  const webcamRef = useRef<Webcam>(null);
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTargetIndex, setCurrentTargetIndex] = useState(0);
  const [capturedFrames, setCapturedFrames] = useState(0);
  const [totalProgress, setTotalProgress] = useState(0);
  const [showCountdown, setShowCountdown] = useState(true);
  const [countdown, setCountdown] = useState(3);

  const targets: CalibrationTarget[] = [
    { id: 0, x: 50, y: 50, captureCount: 0, isActive: false },
    { id: 1, x: screenInfo.width - 50, y: 50, captureCount: 0, isActive: false },
    { id: 2, x: screenInfo.width - 50, y: screenInfo.height - 50, captureCount: 0, isActive: false },
    { id: 3, x: 50, y: screenInfo.height - 50, captureCount: 0, isActive: false },
  ];

  const enterFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } catch (error) {
      console.error('Failed to enter fullscreen:', error);
    }
  }, []);

  const exitFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  }, []);

  useEffect(() => {
    enterFullscreen();
    
    return () => {
      exitFullscreen();
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
      }
    };
  }, [enterFullscreen, exitFullscreen]);

  useEffect(() => {
    if (showCountdown && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0) {
      setShowCountdown(false);
      startCalibration();
    }
  }, [countdown, showCountdown]);

  const captureFrame = useCallback(async () => {
    if (!webcamRef.current) return;
    
    try {
      const imageSrc = webcamRef.current.getScreenshot();
      if (!imageSrc) return;

      const currentTarget = targets[currentTargetIndex];
      await calibrationApi.sendFrame({
        session_id: sessionId,
        frame_data: imageSrc,
        timestamp: Date.now(),
        target_position: {
          x: currentTarget.x,
          y: currentTarget.y,
        },
      });

      setCapturedFrames(prev => prev + 1);
      setTotalProgress(((currentTargetIndex * FRAMES_PER_TARGET + capturedFrames + 1) / (targets.length * FRAMES_PER_TARGET)) * 100);
    } catch (error) {
      console.error('Failed to capture frame:', error);
    }
  }, [currentTargetIndex, sessionId, capturedFrames]);

  const startCalibration = () => {
    captureIntervalRef.current = setInterval(() => {
      captureFrame();
    }, CAPTURE_INTERVAL);
  };

  useEffect(() => {
    if (capturedFrames >= FRAMES_PER_TARGET) {
      if (currentTargetIndex < targets.length - 1) {
        setCurrentTargetIndex(prev => prev + 1);
        setCapturedFrames(0);
      } else {
        if (captureIntervalRef.current) {
          clearInterval(captureIntervalRef.current);
        }
        onComplete({ success: true, message: 'Calibration completed successfully!' });
      }
    }
  }, [capturedFrames, currentTargetIndex, targets.length, onComplete]);

  const currentTarget = targets[currentTargetIndex];

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        bgcolor: 'black',
        cursor: 'none',
      }}
    >
      <Webcam
        ref={webcamRef}
        audio={false}
        screenshotFormat="image/jpeg"
        style={{ display: 'none' }}
      />

      {showCountdown ? (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'white',
            textAlign: 'center',
          }}
        >
          <Typography variant="h1" sx={{ fontSize: '120px', fontWeight: 'bold' }}>
            {countdown}
          </Typography>
          <Typography variant="h4" sx={{ mt: 2 }}>
            Get Ready...
          </Typography>
        </Box>
      ) : (
        <>
          <Box
            sx={{
              position: 'absolute',
              left: currentTarget.x - 20,
              top: currentTarget.y - 20,
              width: 40,
              height: 40,
              borderRadius: '50%',
              bgcolor: 'red',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                bgcolor: 'white',
              }}
            />
          </Box>

          <Box
            sx={{
              position: 'absolute',
              bottom: 40,
              left: '50%',
              transform: 'translateX(-50%)',
              width: '80%',
              maxWidth: 600,
            }}
          >
            <Typography variant="body1" sx={{ color: 'white', mb: 1, textAlign: 'center' }}>
              Look at the red dot - Target {currentTargetIndex + 1} of {targets.length}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={totalProgress}
              sx={{
                height: 10,
                borderRadius: 5,
                bgcolor: 'rgba(255,255,255,0.3)',
                '& .MuiLinearProgress-bar': {
                  bgcolor: 'white',
                },
              }}
            />
            <Typography variant="caption" sx={{ color: 'white', mt: 1, display: 'block', textAlign: 'center' }}>
              {Math.round(totalProgress)}% Complete
            </Typography>
          </Box>

          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              top: 20,
              right: 20,
              color: 'white',
              opacity: 0.7,
            }}
          >
            Press ESC to exit fullscreen
          </Typography>
        </>
      )}
    </Box>
  );
}

export default CalibrationTargets;