import axios from 'axios'

// Base URL for the prediction backend
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? 'https://chest-x-ray-analysis.onrender.com' : 'http://localhost:8000')
).replace(/\/+$/, '')

/**
 * Axios instance with default configuration for the X-ray diagnosis API.
 * The request interceptor automatically injects the Bearer token from
 * localStorage into every outgoing request.
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 second timeout for deep learning inference on cloud CPU
})

// ── Request interceptor — inject JWT token automatically ────────
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('xray_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor — handle 401 globally ──────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear storage and redirect
      localStorage.removeItem('xray_token')
      localStorage.removeItem('xray_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ─────────────────────────────────────────────────────────────────
// Auth API calls
// ─────────────────────────────────────────────────────────────────

/**
 * Register a new user.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ access_token: string, token_type: string }>}
 */
export const registerUser = async (email, password) => {
  const response = await apiClient.post('/auth/register', { email, password })
  return response.data
}

/**
 * Login with email + password.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ access_token: string, token_type: string }>}
 */
export const loginUser = async (email, password) => {
  const response = await apiClient.post('/auth/login', { email, password })
  return response.data
}

// ─────────────────────────────────────────────────────────────────
// Prediction API call
// ─────────────────────────────────────────────────────────────────

/**
 * Sends an X-ray image to the backend for disease prediction.
 * Token is injected automatically by the request interceptor.
 *
 * @param {File} imageFile - The image file to analyze
 * @returns {Promise<{ disease: string, confidence: number, report: string }>}
 */
export const predictDisease = async (imageFile) => {
  const formData = new FormData()
  formData.append('file', imageFile)

  const response = await apiClient.post('/predict', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

// ─────────────────────────────────────────────────────────────────
// Reports API call
// ─────────────────────────────────────────────────────────────────

/**
 * Fetches all saved reports for the currently authenticated user.
 * @returns {Promise<Array<{ id, image_path, disease, confidence, created_at }>>}
 */
export const getReports = async () => {
  const response = await apiClient.get('/reports')
  return response.data
}

export default apiClient
