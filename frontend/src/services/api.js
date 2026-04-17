import axios from 'axios'

// Base URL for the prediction backend
const API_BASE_URL = 'http://localhost:8000'

/**
 * Axios instance with default configuration for the X-ray diagnosis API.
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout for image processing
})

/**
 * Sends an X-ray image to the backend for disease prediction.
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

export default apiClient
