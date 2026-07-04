import axios from 'axios';

const LOCAL_API_BASE = 'http://localhost:8090';
const PROD_API_BASE = 'https://citizens-india-backend-564262191703.us-central1.run.app';

function getApiBase() {
  if (process.env.REACT_APP_API_BASE) return process.env.REACT_APP_API_BASE;
  if (typeof window === 'undefined') return '';

  const { hostname } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return LOCAL_API_BASE;
  }

  return PROD_API_BASE;
}

const api = axios.create({
  baseURL: getApiBase(),
  timeout: 30000,
});

export default api;
