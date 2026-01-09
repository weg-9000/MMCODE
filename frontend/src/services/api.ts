/**
 * API client configuration and base utilities
 * Centralized API configuration with interceptors
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * API configuration
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const API_TIMEOUT = 30000; // 30 seconds

/**
 * Create axios instance with default configuration
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor for adding auth tokens, etc.
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor for error handling
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle specific error cases
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Handle unauthorized
          localStorage.removeItem('auth_token');
          // Optionally redirect to login
          break;
        case 403:
          // Handle forbidden
          console.error('Access forbidden');
          break;
        case 404:
          // Handle not found
          console.error('Resource not found');
          break;
        case 500:
          // Handle server error
          console.error('Server error');
          break;
      }
    } else if (error.request) {
      // Network error
      console.error('Network error - no response received');
    }
    return Promise.reject(error);
  }
);

/**
 * API error type
 */
export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

/**
 * Extract error information from axios error
 */
export function extractApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    return {
      status: axiosError.response?.status || 500,
      message: axiosError.response?.data?.message || axiosError.message,
      detail: axiosError.response?.data?.detail,
    };
  }
  return {
    status: 500,
    message: error instanceof Error ? error.message : 'Unknown error',
  };
}

/**
 * Generic API request helper
 */
export async function apiRequest<T>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  url: string,
  data?: unknown,
  config?: Partial<InternalAxiosRequestConfig>
): Promise<T> {
  const response = await apiClient.request<T>({
    method,
    url,
    data,
    ...config,
  });
  return response.data;
}

export default apiClient;
