# FTO Audit Application

Web-based Flight Training Organisation (FTO) Audit & Compliance System with 13-section regulatory checklist, lead/auditor role segregation, real-time synchronization, and automated Excel reporting.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Goddzzilla3895/fto-audit-app)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template?template=https://github.com/Goddzzilla3895/fto-audit-app)

---

## Features
- **Role-Based Portals**:
  - `/master`: Lead Auditor (Srinivas Rao) — executive oversight, 13-section review, divergence resolution, report generation.
  - `/auditor1`: Assigned Auditor (Sunny Sharma) — field audit checklists, findings, evidence upload.
  - `/`: Central team portal.
- **Mobile-First Tables**:
  - Fixed-layout table dimensions with automatic text wrapping.
  - 4-row content clamp with instant tap-to-reveal.
  - Sticky first column for seamless horizontal scanning.
- **Automated Excel Export**:
  - Generates consolidated audit workbook with native Excel DataValidation dropdowns.
  - Lock-free, in-memory streamed downloads.
- **SQLite Database Persistence**:
  - Zero browser temp-memory reliance; state is committed to SQLite immediately on edit.

---

## Quick Deploy (24/7 Cloud Hosting)

### Option 1: Render (Recommended - Free)
1. Click the **[Deploy to Render](https://render.com/deploy?repo=https://github.com/Goddzzilla3895/fto-audit-app)** button above.
2. Sign in with GitHub (`Goddzzilla3895`).
3. Click **Apply / Create Web Service**.
4. Render will build and deploy your app with a permanent 24/7 HTTPS URL (e.g., `https://fto-audit-app.onrender.com`).

### Option 2: Railway
1. Click the **[Deploy on Railway](https://railway.app/template?template=https://github.com/Goddzzilla3895/fto-audit-app)** button above.
2. Sign in with GitHub and click **Deploy**.
