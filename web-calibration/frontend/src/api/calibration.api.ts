import { apiClient } from './axios.config';

export interface CreateSessionRequest {
  candidate_id: string;
  session_type?: string;
}

export interface CreateSessionResponse {
  session_id: string;
  candidate_id: string;
  created_at: string;
  status: string;
}

export interface ScreenInfoRequest {
  candidate_id: string;
  screen_width_px: number;
  screen_height_px: number;
  dpi?: number;
}

export interface StartCalibrationRequest {
  session_id: string;
  candidate_id: string;
  calibration_type?: string;
}

export interface FrameData {
  session_id: string;
  candidate_id: string;
  frame_data: string;
  frame_index: number;
  target_position: {
    x: number;
    y: number;
  };
  target_index: number;
}

export interface CompleteCalibrationRequest {
  session_id: string;
  candidate_id: string;
}

export interface CalibrationResult {
  success: boolean;
  message: string;
  files_generated?: string[];
  calibration_quality?: number;
}

export const calibrationApi = {
  createSession: async (data: CreateSessionRequest): Promise<CreateSessionResponse> => {
    const response = await apiClient.post('/api/calibration/session/create', data);
    return response.data;
  },

  saveScreenInfo: async (data: ScreenInfoRequest): Promise<void> => {
    await apiClient.post('/api/screen/info', data);
  },

  startCalibration: async (data: StartCalibrationRequest): Promise<void> => {
    await apiClient.post('/api/calibration/start', data);
  },

  sendFrame: async (data: FrameData): Promise<void> => {
    await apiClient.post('/api/calibration/frame', data);
  },

  /**
   * New binary-upload variant – avoids Base64 inflation.
   * `frame` is a Blob (e.g. from canvas.toBlob or MediaStreamTrack). The
   * caller must supply target coords separately.
   */
  sendFrameUpload: async (params: {
    session_id: string;
    candidate_id: string;
    frame_index: number;
    target_index: number;
    target_x: number;
    target_y: number;
    frame: Blob;
  }): Promise<void> => {
    const form = new FormData();
    form.append('session_id', params.session_id);
    form.append('candidate_id', params.candidate_id);
    form.append('frame_index', params.frame_index.toString());
    form.append('target_index', params.target_index.toString());
    form.append('target_x', params.target_x.toString());
    form.append('target_y', params.target_y.toString());
    form.append('frame', params.frame, 'frame.jpg');

    await apiClient.post('/api/calibration/frame/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  completeCalibration: async (data: CompleteCalibrationRequest): Promise<CalibrationResult> => {
    const response = await apiClient.post('/api/calibration/complete', data);
    return response.data;
  },
};