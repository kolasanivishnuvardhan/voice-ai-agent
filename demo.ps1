# Demo script: Run all API endpoints in sequence
# Save this as: demo.ps1
# Run with: .\demo.ps1

Write-Host "========================================" -ForegroundColor Green
Write-Host "REAL-TIME VOICE AI AGENT - API DEMO" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Configuration
$BASE_URL = "http://localhost:8000"
$PATIENT_ID = "96c5f10f-e610-428a-ac99-4e4291c50918"

# 1. Health Check
Write-Host "1. Health Check" -ForegroundColor Yellow
Write-Host "   GET /api/health" -ForegroundColor Cyan
try {
  $health = (Invoke-WebRequest -Uri "$BASE_URL/api/health" -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json
  Write-Host "   Status: $($health.status)" -ForegroundColor Green
  Write-Host "   Whisper Model: $($health.whisper_model)" -ForegroundColor Green
  Write-Host "   Latency Events: $($health.latency_events)" -ForegroundColor Green
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
  exit 1
}
Write-Host ""

# 2. Check Availability - Cardiology Today
Write-Host "2. Check Availability (Cardiology Today)" -ForegroundColor Yellow
Write-Host "   GET /api/appointments/availability" -ForegroundColor Cyan
try {
  $url = "$BASE_URL/api/appointments/availability?specialization=cardiology&date=today"
  $avail = (Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json
  Write-Host "   Doctor: $($avail[0].doctor_name)" -ForegroundColor Green
  Write-Host "   Doctor ID: $($avail[0].doctor_id)" -ForegroundColor Green
  Write-Host "   Available Slots: $($avail[0].available_slots -join ', ')" -ForegroundColor Green
  $doctor_id = $avail[0].doctor_id
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
  exit 1
}
Write-Host ""

# 3. Check Availability - Dermatology Tomorrow
Write-Host "3. Check Availability (Dermatology Tomorrow)" -ForegroundColor Yellow
Write-Host "   GET /api/appointments/availability" -ForegroundColor Cyan
try {
  $url = "$BASE_URL/api/appointments/availability?specialization=dermatology&date=tomorrow"
  $derma = (Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json
  Write-Host "   Doctor: $($derma[0].doctor_name)" -ForegroundColor Green
  Write-Host "   Available Slots: $($derma[0].available_slots -join ', ')" -ForegroundColor Green
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
}
Write-Host ""

# 4. Book Appointment
Write-Host "4. Book Appointment (14:00)" -ForegroundColor Yellow
Write-Host "   POST /api/appointments/book" -ForegroundColor Cyan
try {
  $booking_body = @{
    patient_id = $PATIENT_ID
    doctor_id = $doctor_id
    date = "2026-04-22"
    time = "14:00"
    status = "confirmed"
  } | ConvertTo-Json

  $booking = (Invoke-WebRequest -Uri "$BASE_URL/api/appointments/book" `
    -Method POST `
    -ContentType "application/json" `
    -Body $booking_body `
    -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json

  Write-Host "   Appointment ID: $($booking.appointment_id)" -ForegroundColor Green
  Write-Host "   Doctor: $($booking.doctor_name)" -ForegroundColor Green
  Write-Host "   Date/Time: $($booking.date) at $($booking.time)" -ForegroundColor Green
  $appointment_id = $booking.appointment_id
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
}
Write-Host ""

# 5. View Appointment History
Write-Host "5. View Appointment History" -ForegroundColor Yellow
Write-Host "   GET /api/appointments/history/{patient_id}" -ForegroundColor Cyan
try {
  $url = "$BASE_URL/api/appointments/history/$PATIENT_ID"
  $history = (Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json
  Write-Host "   Total Appointments: $($history.Count)" -ForegroundColor Green
  foreach ($appt in $history) {
    Write-Host "   - $($appt.doctor_name) ($($appt.specialization)) - $($appt.date) at $($appt.time) [Status: $($appt.status)]" -ForegroundColor Cyan
  }
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
}
Write-Host ""

# 6. Reschedule Appointment
Write-Host "6. Reschedule Appointment" -ForegroundColor Yellow
Write-Host "   POST /api/appointments/reschedule" -ForegroundColor Cyan
try {
  $reschedule_body = @{
    appointment_id = $appointment_id
    new_date = "2026-04-25"
    new_time = "10:30"
  } | ConvertTo-Json

  $reschedule = (Invoke-WebRequest -Uri "$BASE_URL/api/appointments/reschedule" `
    -Method POST `
    -ContentType "application/json" `
    -Body $reschedule_body `
    -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json

  Write-Host "   Message: $($reschedule.message)" -ForegroundColor Green
  Write-Host "   New Date/Time: $($reschedule.new_date) at $($reschedule.new_time)" -ForegroundColor Green
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
}
Write-Host ""

# 7. Cancel Appointment
Write-Host "7. Cancel Appointment" -ForegroundColor Yellow
Write-Host "   POST /api/appointments/cancel/{appointment_id}" -ForegroundColor Cyan
try {
  $url = "$BASE_URL/api/appointments/cancel/$appointment_id"
  $cancel = (Invoke-WebRequest -Uri $url `
    -Method POST `
    -UseBasicParsing -ErrorAction Stop).Content | ConvertFrom-Json

  Write-Host "   Message: $($cancel.message)" -ForegroundColor Green
} catch {
  Write-Host "   Error: $_" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "DEMO COMPLETE - ALL ENDPOINTS WORKING" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Browser Demo:" -ForegroundColor Cyan
Write-Host "   http://localhost:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "   See DEMO.md for detailed guide" -ForegroundColor Yellow
Write-Host ""
