export interface CalibrationSession {
  sessionId: string;
  candidateId: string;
  status: 'idle' | 'screen_setup' | 'camera_check' | 'calibrating' | 'completed' | 'error';
  screenInfo?: ScreenInfo;
  calibrationData?: CalibrationData;
  error?: string;
}

export interface ScreenInfo {
  width: number;
  height: number;
  dpi: number;
  physicalWidth?: number;
  physicalHeight?: number;
}

export interface CalibrationTarget {
  id: number;
  x: number;
  y: number;
  captureCount: number;
  isActive: boolean;
}

export interface CalibrationData {
  targets: CalibrationTarget[];
  currentTargetIndex: number;
  framesPerTarget: number;
  capturedFrames: number;
  quality: number;
}

export interface WebcamFrame {
  data: string;
  timestamp: number;
  targetPosition?: { x: number; y: number };
}

export interface CalibrationResult {
  success: boolean;
  message: string;
  filesGenerated?: string[];
  quality?: number;
}