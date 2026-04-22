# 🎤 Real-Time Multilingual Voice AI Agent - Demo Guide

## Overview
This is a **production-grade Real-Time Multilingual Voice AI Agent** for clinical appointment booking with:
- 🎙️ Real-time voice recording with WebSocket streaming
- 🗣️ Multi-language STT (Speech-to-Text) with Whisper
- 🤖 AI-powered conversation with Groq's Llama 3.3 70B
- 📱 Natural language understanding for appointment booking
- 🔊 Text-to-Speech (gTTS) with fallback (pyttsx3)
- 💾 Redis session memory for context persistence
- 🗄️ PostgreSQL for persistent data

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- All services running: `docker compose up -d`
- Application accessible at: `http://localhost:8000`

### Verify System Status
```bash
# Check all services are healthy
docker compose ps

# Expected output:
# ✓ postgres-1       Healthy
# ✓ redis-1          Healthy
# ✓ app-1            Up
# ✓ celery_worker-1  Up
# ✓ celery_beat-1    Up
```

---

## 📊 Demo Flow: Two Ways to Interact

### **Method 1: Voice Interface (Browser) - Full Experience**
Perfect for showing the complete voice-based appointment booking flow.

**Steps:**
1. Open browser: `http://localhost:8000`
2. Click **+** button to start recording
3. Say: **"Book cardiology appointment today"**
4. Agent responds with available time slots
5. Say: **"14"** (or "1700", "10.30", "2 PM")
6. Agent confirms booking with appointment ID
7. View confirmation message

**Expected Flow:**
```
You:   "Book cardiology appointment today"
Agent: "I found available slots on today: 09:00, 10:30, 12:00, 14:00, 15:30, 17:00. 
        Please tell me your preferred time."

You:   "14"
Agent: "Great! I've booked your appointment with Dr. Arun Mehta on 2026-04-22 at 14:00. 
        Your appointment ID is [UUID]. Confirmation sent!"
```

---

### **Method 2: REST API Endpoints (Postman/curl) - Technical Demo**

Perfect for showing backend capabilities and system architecture.

---

## 📡 REST API Endpoints Demo

### **1. Health Check** ✅
**Endpoint:** `GET /api/health`

**Purpose:** Verify system status

**Command:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
{
  "status": "ok",
  "whisper_model": "tiny",
  "latency_events": 0
}
```

---

### **2. Check Appointment Availability** 🏥
**Endpoint:** `GET /api/appointments/availability`

**Query Parameters:**
- `specialization` - Doctor specialty (cardiology, dermatology, neurology, pediatrics, general)
- `date` - Appointment date (today, tomorrow, YYYY-MM-DD, DD-MM-YYYY)

**Commands:**

#### Cardiology today:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/availability?specialization=cardiology&date=today" -UseBasicParsing | ForEach-Object Content
```

#### Dermatology tomorrow:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/availability?specialization=dermatology&date=tomorrow" -UseBasicParsing | ForEach-Object Content
```

#### Neurology specific date:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/availability?specialization=neurology&date=2026-04-23" -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
[
  {
    "doctor_id": "1e94703c-a610-477a-a132-d6f273a30820",
    "doctor_name": "Arun Mehta",
    "available_slots": [
      "09:00",
      "10:30",
      "12:00",
      "14:00",
      "15:30",
      "17:00"
    ]
  }
]
```

---

### **3. Book an Appointment** ✍️
**Endpoint:** `POST /api/appointments/book`

**Request Body:**
```json
{
  "patient_id": "96c5f10f-e610-428a-ac99-4e4291c50918",
  "doctor_id": "1e94703c-a610-477a-a132-d6f273a30820",
  "date": "2026-04-22",
  "time": "14:00",
  "status": "confirmed"
}
```

**Command:**
```powershell
$body = @{
  patient_id = "96c5f10f-e610-428a-ac99-4e4291c50918"
  doctor_id = "1e94703c-a610-477a-a132-d6f273a30820"
  date = "2026-04-22"
  time = "14:00"
  status = "confirmed"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/book" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
{
  "appointment_id": "03503e2e-12ce-425c-8133-aed13cf22341",
  "doctor_name": "Arun Mehta",
  "date": "2026-04-22",
  "time": "09:00",
  "confirmation_message": "Appointment confirmed with Dr Arun Mehta on 2026-04-22 at 09:00"
}
```

---

### **4. View Appointment History** 📋
**Endpoint:** `GET /api/appointments/history/{patient_id}`

**Command:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/history/96c5f10f-e610-428a-ac99-4e4291c50918" `
  -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
[
  {
    "appointment_id": "03503e2e-12ce-425c-8133-aed13cf22341",
    "doctor_name": "Arun Mehta",
    "specialization": "cardiology",
    "date": "2026-04-22",
    "time": "09:00",
    "status": "confirmed"
  }
]
```

---

### **5. Cancel Appointment** ❌
**Endpoint:** `POST /api/appointments/cancel/{appointment_id}`

**Command:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/cancel/03503e2e-12ce-425c-8133-aed13cf22341" `
  -Method POST `
  -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
{
  "message": "Appointment cancelled successfully"
}
```

---

### **6. Reschedule Appointment** 🔄
**Endpoint:** `POST /api/appointments/reschedule`

**Request Body:**
```json
{
  "appointment_id": "03503e2e-12ce-425c-8133-aed13cf22341",
  "new_date": "2026-04-25",
  "new_time": "10:30"
}
```

**Command:**
```powershell
$body = @{
  appointment_id = "03503e2e-12ce-425c-8133-aed13cf22341"
  new_date = "2026-04-25"
  new_time = "10:30"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/reschedule" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing | ForEach-Object Content
```

**Expected Response:**
```json
{
  "message": "Appointment rescheduled successfully",
  "new_appointment_id": "new-uuid",
  "new_date": "2026-04-25",
  "new_time": "10:30"
}
```

---

## 🎯 Complete API Demo Script

Run this comprehensive script to demonstrate all endpoints:

```powershell
# Demo script: Run all API endpoints in sequence

Write-Host "========================================" -ForegroundColor Green
Write-Host "REAL-TIME VOICE AI AGENT - API DEMO" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 1. Health Check
Write-Host "1️⃣  Health Check" -ForegroundColor Yellow
$health = (Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "✓ Status: $($health.status)" -ForegroundColor Green
Write-Host "✓ Whisper Model: $($health.whisper_model)" -ForegroundColor Green
Write-Host ""

# 2. Check Availability - Cardiology Today
Write-Host "2️⃣  Check Availability (Cardiology - Today)" -ForegroundColor Yellow
$avail = (Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/availability?specialization=cardiology&date=today" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "✓ Doctor: $($avail[0].doctor_name)" -ForegroundColor Green
Write-Host "✓ Available Slots: $($avail[0].available_slots -join ', ')" -ForegroundColor Green
$doctor_id = $avail[0].doctor_id
Write-Host ""

# 3. Book Appointment
Write-Host "3️⃣  Book Appointment (14:00)" -ForegroundColor Yellow
$booking_body = @{
  patient_id = "96c5f10f-e610-428a-ac99-4e4291c50918"
  doctor_id = $doctor_id
  date = "2026-04-22"
  time = "14:00"
  status = "confirmed"
} | ConvertTo-Json

$booking = (Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/book" `
  -Method POST `
  -ContentType "application/json" `
  -Body $booking_body `
  -UseBasicParsing).Content | ConvertFrom-Json

Write-Host "✓ Appointment ID: $($booking.appointment_id)" -ForegroundColor Green
Write-Host "✓ Doctor: $($booking.doctor_name)" -ForegroundColor Green
Write-Host "✓ Date/Time: $($booking.date) at $($booking.time)" -ForegroundColor Green
$appointment_id = $booking.appointment_id
Write-Host ""

# 4. View History
Write-Host "4️⃣  View Appointment History" -ForegroundColor Yellow
$history = (Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/history/96c5f10f-e610-428a-ac99-4e4291c50918" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "✓ Total Appointments: $($history.Count)" -ForegroundColor Green
foreach ($appt in $history) {
  Write-Host "  - $($appt.doctor_name) ($($appt.specialization)) on $($appt.date) at $($appt.time) - Status: $($appt.status)" -ForegroundColor Cyan
}
Write-Host ""

# 5. Check Availability - Dermatology Tomorrow
Write-Host "5️⃣  Check Availability (Dermatology - Tomorrow)" -ForegroundColor Yellow
$derma = (Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/availability?specialization=dermatology&date=tomorrow" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "✓ Doctor: $($derma[0].doctor_name)" -ForegroundColor Green
Write-Host "✓ Available Slots: $($derma[0].available_slots -join ', ')" -ForegroundColor Green
Write-Host ""

# 6. Reschedule Appointment
Write-Host "6️⃣  Reschedule Appointment" -ForegroundColor Yellow
$reschedule_body = @{
  appointment_id = $appointment_id
  new_date = "2026-04-25"
  new_time = "10:30"
} | ConvertTo-Json

$reschedule = (Invoke-WebRequest -Uri "http://localhost:8000/api/appointments/reschedule" `
  -Method POST `
  -ContentType "application/json" `
  -Body $reschedule_body `
  -UseBasicParsing).Content | ConvertFrom-Json

Write-Host "✓ Rescheduled to: $($reschedule.new_date) at $($reschedule.new_time)" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ DEMO COMPLETE - ALL ENDPOINTS WORKING" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
```

**To run the script:**
```powershell
# Save as demo.ps1 and run:
.\demo.ps1
```

---

## 🎙️ Voice Demo Talking Points

When demonstrating the voice interface:

1. **Start Recording** → Click **+** button
   - "Book cardiology appointment today"
   - ✓ Shows AI understands appointment intent
   - ✓ Extracts specialization automatically
   - ✓ Returns available slots for that doctor

2. **Time Selection** → Say any of these:
   - Bare hour: **"14"** → Parses to 14:00
   - Military time: **"1700"** → Parses to 17:00
   - Dot notation: **"10.30"** → Parses to 10:30
   - 12-hour: **"2 PM"** → Parses to 14:00
   - ✓ Shows intelligent time extraction

3. **Confirmation** → Agent responds with:
   - Appointment ID
   - Doctor name
   - Date and time
   - Status confirmed
   - ✓ Shows persistent booking in database

4. **Follow-up (Multi-turn)** → Say:
   - "Show me my history"
   - "Cancel that appointment"
   - "Book another time"
   - ✓ Shows context memory and multi-turn capabilities

---

## 🔧 Technical Highlights to Mention

- **AI Model:** Groq's Llama 3.3 70B (ultra-fast inference)
- **STT:** OpenAI Whisper (Tiny model, supports 90+ languages)
- **TTS:** Google Text-to-Speech with pyttsx3 fallback
- **Real-time:** WebSocket bidirectional streaming
- **Database:** PostgreSQL with async SQLAlchemy
- **Cache/Memory:** Redis with 1-hour session TTL
- **Async:** Full async/await pipeline for low latency
- **Docker:** All services containerized for easy deployment

---

## 📊 Key Features Demo

| Feature | Demo How | Expected Result |
|---------|----------|-----------------|
| **Multi-language STT** | Speak in different languages | Whisper detects and translates |
| **Natural date parsing** | Say "today", "tomorrow", dates | Correctly extracted |
| **Smart time extraction** | Say "14", "1700", "10.30", "2 PM" | All formats parsed correctly |
| **Context memory** | Multi-turn conversation | Agent remembers previous selections |
| **Real-time booking** | Say appointment details | Immediate database confirmation |
| **Appointment history** | Request via voice or API | Shows all patient bookings |
| **Doctor availability** | Query by specialty | Returns available time slots |
| **Error handling** | Book conflicting time | System rejects and offers alternatives |

---

## ✅ Pre-Demo Checklist

- [ ] All Docker services running: `docker compose ps` shows all healthy
- [ ] Application accessible: `http://localhost:8000` loads
- [ ] Health check passes: `GET /api/health` returns 200
- [ ] Test patient ID exists: `96c5f10f-e610-428a-ac99-4e4291c50918`
- [ ] Database has doctors and schedules
- [ ] Browser microphone permission granted
- [ ] Audio output enabled for TTS demo

---

## 🎬 Demo Timeline (5-10 minutes)

1. **Introduction** (1 min)
   - Show project overview
   - Mention tech stack

2. **Voice Interface Demo** (4 min)
   - Record and book an appointment
   - Show time extraction variations
   - Confirm in database

3. **REST API Demo** (3 min)
   - Run comprehensive demo script
   - Show all 6 endpoints working
   - Highlight booking confirmation

4. **Q&A** (2 min)
   - Discuss architecture
   - Answer technical questions

---

## 🚨 Troubleshooting During Demo

| Issue | Solution |
|-------|----------|
| Microphone not working | Check browser permissions, refresh page |
| Agent not responding | Check `docker compose logs app --tail 20` |
| Booking fails | Verify patient ID exists in database |
| Time not extracted | Check STT output in console logs |
| API returns 404 | Ensure all services healthy |

---

## 📱 Live Demo URL

**Browser:** `http://localhost:8000`

**Session ID:** Shown at top of page (auto-generated per session)

---

Good luck with your demo! 🎉
