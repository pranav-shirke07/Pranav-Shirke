import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;
const ADMIN_TOKEN_KEY = "dial-for-help-admin-token";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

export const getAdminToken = () => localStorage.getItem(ADMIN_TOKEN_KEY);

export const setAdminToken = (token) => {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
};

export const clearAdminToken = () => {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
};

const withAdminHeaders = () => ({
  headers: {
    Authorization: `Bearer ${getAdminToken()}`,
  },
});

export const publicApi = {
  createBooking: async (payload) => {
    const response = await client.post("/bookings", payload);
    return response.data;
  },
  createWorkerSignup: async (payload) => {
    const response = await client.post("/workers/signup", payload);
    return response.data;
  },
  createContact: async (payload) => {
    const response = await client.post("/contacts", payload);
    return response.data;
  },
};

export const adminApi = {
  login: async (payload) => {
    const response = await client.post("/admin/login", payload);
    return response.data;
  },
  logout: async () => {
    const response = await client.post("/admin/logout", {}, withAdminHeaders());
    return response.data;
  },
  getOverview: async () => {
    const response = await client.get("/admin/overview", withAdminHeaders());
    return response.data;
  },
  updateBookingStatus: async (bookingId, payload) => {
    const response = await client.patch(
      `/admin/bookings/${bookingId}/status`,
      payload,
      withAdminHeaders(),
    );
    return response.data;
  },
};
