import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { MainLayout } from "@/components/MainLayout";
import HomePage from "@/pages/HomePage";
import BookingPage from "@/pages/BookingPage";
import WorkerSignupPage from "@/pages/WorkerSignupPage";
import ContactPage from "@/pages/ContactPage";
import TrackBookingPage from "@/pages/TrackBookingPage";
import AllServicesPage from "@/pages/AllServicesPage";
import UserAuthPage from "@/pages/UserAuthPage";
import UserProfilePage from "@/pages/UserProfilePage";
import UserNotificationsPage from "@/pages/UserNotificationsPage";
import AdminLoginPage from "@/pages/AdminLoginPage";
import AdminDashboardPage from "@/pages/AdminDashboardPage";

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<HomePage />} />
            <Route path="book" element={<BookingPage />} />
            <Route path="track-booking" element={<TrackBookingPage />} />
            <Route path="services" element={<AllServicesPage />} />
            <Route path="account/auth" element={<UserAuthPage />} />
            <Route path="account/profile" element={<UserProfilePage />} />
            <Route path="account/notifications" element={<UserNotificationsPage />} />
            <Route path="worker-signup" element={<WorkerSignupPage />} />
            <Route path="contact" element={<ContactPage />} />
          </Route>
          <Route path="/admin" element={<AdminLoginPage />} />
          <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors closeButton position="top-right" />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
