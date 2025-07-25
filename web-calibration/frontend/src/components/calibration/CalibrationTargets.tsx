import { useState, useEffect, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Box, Typography, LinearProgress } from '@mui/material';
import { calibrationApi } from '../../api/calibration.api';
import { ScreenInfo, CalibrationTarget } from '../../types/calibration.types';

interface CalibrationTargetsProps {
  sessionId: string;
  candidateId: string;
  screenInfo: ScreenInfo;
  onComplete: (result: { success: boolean; message: string }) => void;
}

const FRAMES_PER_TARGET = 30;
const CAPTURE_INTERVAL = 100; // milliseconds
const WEBCAM_WIDTH = 640;
const WEBCAM_HEIGHT = 480;

function CalibrationTargets({ sessionId, candidateId, screenInfo, onComplete }: CalibrationTargetsProps) {
  const webcamRef = useRef<Webcam>(null);
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [, setIsFullscreen] = useState(false);
  const [currentTargetIndex, setCurrentTargetIndex] = useState(0);
  const [capturedFrames, setCapturedFrames] = useState(0);
  const [totalProgress, setTotalProgress] = useState(0);
  const [showCountdown, setShowCountdown] = useState(true);
  const [countdown, setCountdown] = useState(3);
  const [webcamReady, setWebcamReady] = useState(false);
  const [debugVisible, setDebugVisible] = useState(false); // Hide webcam by default after debugging
  
  // Use refs to avoid closure issues in interval callback
  const currentTargetIndexRef = useRef(0);
  const capturedFramesRef = useRef(0);
  
  const handleUserMedia = useCallback(() => {
    console.log('[WEBCAM] User media available');
    setWebcamReady(true);
    
    // Wait for video to be fully loaded before testing
    setTimeout(() => {
      if (webcamRef.current?.video) {
        const video = webcamRef.current.video;
        console.log('[WEBCAM] Video element:', video);
        console.log('[WEBCAM] Video dimensions:', video.videoWidth, 'x', video.videoHeight);
        console.log('[WEBCAM] Video readyState:', video.readyState);
        
        const testShot = webcamRef.current.getScreenshot();
        console.log('[WEBCAM] Test screenshot:', {
          length: testShot?.length || 0,
          preview: testShot?.slice(0, 50) || 'null'
        });
      }
    }, 2000); // Wait longer for video to load
  }, []);

  const handleUserMediaError = useCallback((error: string | DOMException) => {
    console.error('[WEBCAM] User media error:', error);
    setWebcamReady(false);
  }, []);

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
    if (!webcamRef.current) {
      console.log('[CAPTURE] Webcam ref not available');
      return;
    }
    
    // Check video readiness
    const video = webcamRef.current.video;
    if (!video || video.readyState < 4) {
      console.log('[CAPTURE] Video not ready, readyState:', video?.readyState);
      return;
    }
    
    try {
      const imageSrc = webcamRef.current.getScreenshot();

      if (!imageSrc || imageSrc === 'data:,' || imageSrc.length < 100) {
        console.log('[CAPTURE] Invalid image data:', { length: imageSrc?.length, preview: imageSrc?.slice(0, 50) });
        return;
      }

      const currentTarget = targets[currentTargetIndexRef.current];
      const frameIndex =
        currentTargetIndexRef.current * FRAMES_PER_TARGET +
        capturedFramesRef.current;

      // Debug: inspect the raw base64 string being captured
      console.log('[CAPTURE]', {
        index: frameIndex,
        length: imageSrc.length,
        head: imageSrc.slice(0, 50),
      });
      
      // Convert pixel coordinates to normalized (0-1) space expected by backend
      const normX = currentTarget.x / screenInfo.width;
      const normY = currentTarget.y / screenInfo.height;

      await calibrationApi.sendFrame({
        session_id: sessionId,
        candidate_id: candidateId,
        frame_data: imageSrc,
        frame_index: frameIndex,
        target_position: {
          x: normX,
          y: normY,
        },
        target_index: currentTargetIndexRef.current,
      });

      capturedFramesRef.current += 1;
      setCapturedFrames(capturedFramesRef.current);
      
      console.log(`[PROGRESS] Target ${currentTargetIndexRef.current + 1}, Frame ${capturedFramesRef.current}/${FRAMES_PER_TARGET}`);
      
      const progress = ((currentTargetIndexRef.current * FRAMES_PER_TARGET + capturedFramesRef.current) / (targets.length * FRAMES_PER_TARGET)) * 100;
      setTotalProgress(progress);
    } catch (error) {
      console.error('Failed to capture frame:', error);
    }
  }, [sessionId, candidateId, screenInfo.width, screenInfo.height]);

  const startCalibration = useCallback(() => {
    // Wait a bit longer to ensure video is ready
    setTimeout(() => {
      console.log('[CALIBRATION] Starting frame capture');
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
      }
      captureIntervalRef.current = setInterval(() => {
        captureFrame();
      }, CAPTURE_INTERVAL);
    }, 1000);
  }, [captureFrame]);

  useEffect(() => {
    currentTargetIndexRef.current = currentTargetIndex;
  }, [currentTargetIndex]);

  useEffect(() => {
    capturedFramesRef.current = capturedFrames;
  }, [capturedFrames]);

  useEffect(() => {
    console.log(`[TARGET_CHECK] Captured: ${capturedFrames}, Target: ${currentTargetIndex + 1}/${targets.length}`);
    
    if (capturedFrames >= FRAMES_PER_TARGET) {
      if (currentTargetIndex < targets.length - 1) {
        console.log(`[TARGET_MOVE] Moving to target ${currentTargetIndex + 2}`);
        capturedFramesRef.current = 0;
        currentTargetIndexRef.current = currentTargetIndex + 1;
        setCurrentTargetIndex(currentTargetIndex + 1);
        setCapturedFrames(0);
      } else {
        // Calibration complete - stop capture immediately
        if (captureIntervalRef.current) {
          clearInterval(captureIntervalRef.current);
          captureIntervalRef.current = null;
        }
        console.log('[CALIBRATION] Completed - stopping capture');
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
      <Box sx={{ 
        position: 'fixed',
        top: debugVisible ? '10px' : '10px',
        right: debugVisible ? '10px' : '10px',
        width: debugVisible ? '200px' : '200px',
        height: debugVisible ? '150px' : '120px',
        zIndex: debugVisible ? 9999 : 9999,
        border: debugVisible ? '2px solid red' : '1px solid transparent',
        backgroundColor: 'black',
        borderRadius: 1,
        overflow: 'hidden',
        display: debugVisible ? 'block' : 'block' // Always visible for getScreenshot to work
      }}>
        <Webcam
          ref={webcamRef}
          audio={false}
          screenshotFormat="image/jpeg"
          videoConstraints={{
            width: WEBCAM_WIDTH,
            height: WEBCAM_HEIGHT,
            facingMode: 'user'
          }}
          onUserMedia={handleUserMedia}
          onUserMediaError={handleUserMediaError}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        />
      </Box>

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

          <Box sx={{ position: 'absolute', top: 20, right: 20 }}>
            <Typography
              variant="caption"
              sx={{ color: 'white', opacity: 0.7, display: 'block', mb: 1 }}
            >
              Press ESC to exit fullscreen
            </Typography>
            <Typography
              variant="caption"
              sx={{ 
                color: webcamReady ? 'green' : 'red', 
                display: 'block', 
                cursor: 'pointer',
                textDecoration: 'underline'
              }}
              onClick={() => setDebugVisible(!debugVisible)}
            >
              Webcam: {webcamReady ? 'READY' : 'NOT READY'} (click to toggle)
            </Typography>
          </Box>
        </>
      )}
    </Box>
  );
}

export default CalibrationTargets;