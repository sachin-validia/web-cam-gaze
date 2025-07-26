import { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

export function setupDebugInterceptors(axiosInstance: AxiosInstance) {
  // Request interceptor
  axiosInstance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      console.group(`📤 API Request: ${config.method?.toUpperCase()} ${config.url}`);
      console.log('Headers:', config.headers);
      console.log('Data:', config.data);
      console.groupEnd();
      
      // Store request time for response duration calculation
      (config as any).requestTime = Date.now();
      
      return config;
    },
    (error: AxiosError) => {
      console.error('❌ Request Error:', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor
  axiosInstance.interceptors.response.use(
    (response: AxiosResponse) => {
      const duration = Date.now() - ((response.config as any).requestTime || 0);
      
      console.group(`📥 API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`);
      console.log('Status:', response.status);
      console.log('Duration:', `${duration}ms`);
      console.log('Data:', response.data);
      console.groupEnd();
      
      return response;
    },
    (error: AxiosError) => {
      const duration = Date.now() - ((error.config as any)?.requestTime || 0);
      
      console.group(`❌ API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
      console.log('Status:', error.response?.status);
      console.log('Duration:', `${duration}ms`);
      console.log('Error Data:', error.response?.data);
      console.log('Error Message:', error.message);
      console.groupEnd();
      
      // Log specific error details for debugging
      if (error.response?.status === 400) {
        console.error('🔍 400 Bad Request Details:', {
          url: error.config?.url,
          requestData: error.config?.data,
          responseData: error.response?.data,
          responseDetail: (error.response?.data as any)?.detail || 'No detail provided'
        });
      }
      
      return Promise.reject(error);
    }
  );
}