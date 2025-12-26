import { AxiosError } from 'axios';

// API Error response structure
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  [key: string]: unknown;
}

// Extended error type for CORS errors
export interface CorsError extends Error {
  isCorsError: boolean;
  originalError: unknown;
}

// Type guard for CORS errors
export function isCorsError(error: unknown): error is CorsError {
  return error instanceof Error && 'isCorsError' in error && error.isCorsError === true;
}

// Type for API errors
export type ApiError = AxiosError<ApiErrorResponse> | CorsError | Error;

// Type guard for Axios errors
export function isAxiosError(error: unknown): error is AxiosError<ApiErrorResponse> {
  return error instanceof Error && 'isAxiosError' in error;
} 