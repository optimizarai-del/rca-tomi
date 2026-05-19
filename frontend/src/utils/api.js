import axios from 'axios'

// VITE_API_URL puede ser:
//   - undefined  → fallback a http://localhost:8000 (dev sin .env)
//   - "http://host:port"  → dev/prod apuntando a un backend externo
//   - ""  → producción con nginx haciendo proxy_pass al backend en el mismo dominio
const envUrl = import.meta.env.VITE_API_URL
const baseURL = envUrl !== undefined && envUrl !== null
  ? envUrl
  : 'http://localhost:8000'

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api
