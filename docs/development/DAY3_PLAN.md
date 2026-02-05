# 📅 DAY 3 - MULTI-TENANT + ADMIN

**Date:** 5 Feb 2026  
**Goal:** Admin può gestire macchine + Activation flow

---

## 🌅 MORNING SESSION (5h)

### Task 1: Admin Machine Creation (2h)
**Endpoint:** `POST /api/admin/machines`
**Features:**
- Auto-generate activation code (32 chars)
- Create machine instance
- Return QR code data

### Task 2: Machine Management Routes (1.5h)
**Endpoints:**
- GET /api/admin/machines - List all
- GET /api/admin/machines/{id} - Details
- PATCH /api/admin/machines/{id} - Update
- DELETE /api/admin/machines/{id} - Soft delete

### Task 3: User-Machine Access (1.5h)
**Endpoint:** `POST /api/admin/access/grant`
**Purpose:** Assign users to machines
**Updates JWT:** machine_ids in token

---

## 🌆 AFTERNOON SESSION (5h)

### Task 4: Activation Flow (2.5h)
**Endpoints:**
- GET /activate?code=ABC123 - Form
- POST /activate - Register + link

### Task 5: Admin UI Basic (2.5h)
**Templates:** Machine list, create form

---

## ✅ END OF DAY DELIVERABLES
- Admin creates machines
- Activation codes work
- User-machine access functional
- Activation flow complete
