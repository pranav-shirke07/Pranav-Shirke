# PRD — Dial For Help

## Original Problem Statement
- Build website "Dial For Help"

## User Choices Captured
- Fresh custom design (not copying uploaded HTML)
- Full flow: Landing + Booking + Worker Signup + Admin + Contact
- Proper admin auth using email/password
- MongoDB persistence with booking status tracking (`pending`, `assigned`, `completed`)
- Notifications on booking events via Twilio SMS + SendGrid Email to customer + admin
- Subscription policy update:
  - User gets first 2 services free; then ₹99/year mandatory
  - Free usage counted by **phone + email** identity
  - Worker subscription ₹199/year mandatory **before signup submit**
  - Razorpay Test mode integration

## Architecture Decisions
- **Frontend:** React + React Router + Shadcn UI + Tailwind + Framer Motion
- **Backend:** FastAPI + Motor (MongoDB) in single service file for rapid delivery
- **Database Collections:** `bookings`, `workers`, `contacts`, `admins`, `admin_sessions`
- **Auth Model:** Admin session token (bearer token) with expiry in DB
- **Notification Strategy:** Non-blocking notification attempts via `asyncio.to_thread` wrappers around Twilio/SendGrid HTTP calls; booking creation/status updates succeed even if notification config is missing.

## User Personas
- **Customer/Homeowner:** Needs fast, trustworthy household help
- **Service Worker:** Wants to register skills and availability for leads
- **Admin/Operator:** Manages bookings, worker assignment, and status progression

## Core Requirements (Static)
- Conversion-first landing page with strong trust cues
- 3-step booking UX
- Worker onboarding form
- Contact support form
- Admin login + dashboard with booking status updates and assignment
- Mongo-backed data persistence and API endpoints for all major flows
- Testable UI with `data-testid` on interactive and critical elements

## What Has Been Implemented
### 2026-03-22
- Built complete backend API for bookings, worker signup, contact submissions, admin login/logout, dashboard overview, and booking status updates.
- Implemented MongoDB data models and safe API responses excluding BSON `_id` from returned documents.
- Added default admin bootstrap account (`admin@dialforhelp.com` / `Admin@123`) on startup.
- Added Twilio/SendGrid notification hooks for booking create/status events with graceful failure handling.
- Built full frontend experience:
  - Home page with branded visuals and service cards
  - 3-step booking page
  - Worker signup page
  - Contact page
  - Admin login and dashboard (bookings/workers/contacts tabs)
- Added custom visual theme from design guidelines (Clash Display + Manrope, warm stone/orange palette, textured gradient background).
- Added robust `data-testid` coverage across forms, actions, dashboard rows, and key content.
- Fixed booking submit-button validation edge case on step 3.
- Addressed intermittent ResizeObserver overlay by suppressing known benign runtime noise at app bootstrap.
- Completed self-tests + testing-agent round; core flows verified.
- Added annual subscription system with Razorpay integration:
  - New APIs: user/worker subscription status, create-order, verify-payment
  - User booking gate after 2 free bookings (₹99/year)
  - Worker signup gate requiring active ₹199/year plan before submission
  - Frontend Razorpay checkout wiring on booking and worker signup flows
  - Stored provided Razorpay test credentials in backend env for activation

## Prioritized Backlog
### P0 (Next Critical)
- Wire production Twilio + SendGrid credentials and validate real delivery to both customer and admin.
- Add admin password change flow and optional second admin creation.
- Add webhook verification path for Razorpay events (`payment.captured`) as additional server-side reconciliation.

### P1 (Important)
- Add booking filters/search in admin dashboard (date/service/status).
- Add worker assignment suggestions by skill match.
- Add notification delivery history view in admin panel.

### P2 (Enhancement)
- Add customer booking tracking page by booking ID.
- Add analytics cards (conversion funnel, completion rate).
- Add multilingual support and localized service categories.

## Next Tasks
1. Receive Twilio + SendGrid credentials from user and configure env securely.
2. Validate customer/admin notification delivery in live flow.
3. Add lightweight admin account management (change password).
4. Improve dashboard filtering and assignment experience.
