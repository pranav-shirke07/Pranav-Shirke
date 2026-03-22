import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;
const ADMIN_TOKEN_KEY = "dial-for-help-admin-token";
const USER_TOKEN_KEY = "dial-for-help-user-token";

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

export const getUserToken = () => localStorage.getItem(USER_TOKEN_KEY);

export const setUserToken = (token) => {
  localStorage.setItem(USER_TOKEN_KEY, token);
};

export const clearUserToken = () => {
  localStorage.removeItem(USER_TOKEN_KEY);
};

const withAdminHeaders = () => ({
  headers: {
    Authorization: `Bearer ${getAdminToken()}`,
  },
});

const withUserHeaders = () => ({
  headers: {
    Authorization: `Bearer ${getUserToken()}`,
  },
});

export const publicApi = {
  createBooking: async (payload) => {
    const response = await client.post("/bookings", payload);
    return response.data;
  },
  trackBooking: async (bookingId) => {
    const response = await client.get(`/bookings/track/${bookingId}`);
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

export const paymentsApi = {
  getUserSubscriptionStatus: async ({ phone, email }) => {
    const response = await client.get("/subscriptions/user-status", {
      params: { phone, email },
    });
    return response.data;
  },
  getWorkerSubscriptionStatus: async ({ phone, email }) => {
    const response = await client.get("/subscriptions/worker-status", {
      params: { phone, email },
    });
    return response.data;
  },
  createOrder: async (payload) => {
    const response = await client.post("/payments/create-order", payload);
    return response.data;
  },
  verifyOrder: async (payload) => {
    const response = await client.post("/payments/verify", payload);
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
  getSubscriptions: async () => {
    const response = await client.get("/admin/subscriptions", withAdminHeaders());
    return response.data;
  },
  getAnalytics: async () => {
    const response = await client.get("/admin/analytics", withAdminHeaders());
    return response.data;
  },
  getDemoLogins: async () => {
    const response = await client.get("/admin/demo-logins", withAdminHeaders());
    return response.data;
  },
  resetDemoData: async () => {
    const response = await client.post("/admin/demo/reset", {}, withAdminHeaders());
    return response.data;
  },
  resetReseedDemoData: async () => {
    const response = await client.post("/admin/demo/reset-reseed", {}, withAdminHeaders());
    return response.data;
  },
  getWorkerSuggestions: async (bookingId) => {
    const response = await client.get(`/admin/bookings/${bookingId}/suggest-workers`, withAdminHeaders());
    return response.data;
  },
  dispatchRenewalReminders: async () => {
    const response = await client.post("/admin/subscriptions/dispatch-renewal-reminders", {}, withAdminHeaders());
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

export const userApi = {
  register: async (payload) => {
    const response = await client.post("/users/register", payload);
    return response.data;
  },
  login: async (payload) => {
    const response = await client.post("/users/login", payload);
    return response.data;
  },
  logout: async () => {
    const response = await client.post("/users/logout", {}, withUserHeaders());
    return response.data;
  },
  getProfile: async () => {
    const response = await client.get("/users/profile", withUserHeaders());
    return response.data;
  },
  updateProfile: async (payload) => {
    const response = await client.put("/users/profile", payload, withUserHeaders());
    return response.data;
  },
  getMyBookings: async () => {
    const response = await client.get("/users/bookings", withUserHeaders());
    return response.data;
  },
  getNotifications: async () => {
    const response = await client.get("/users/notifications", withUserHeaders());
    return response.data;
  },
  markNotificationRead: async (notificationId) => {
    const response = await client.patch(`/users/notifications/${notificationId}/read`, {}, withUserHeaders());
    return response.data;
  },
};
