const form = document.getElementById("bookingForm");
const navbar = document.getElementById("navbar");
const statusBanner = document.getElementById("statusBanner");
const bookingDateInput = document.getElementById("bookingDate");
const timeSlotSelect = document.getElementById("timeSlot");
const summaryPanel = document.getElementById("summaryPanel");
const successScreen = document.getElementById("successScreen");
const backBtn = document.getElementById("backBtn");
const nextBtn = document.getElementById("nextBtn");
const submitBtn = document.getElementById("submitBtn");

const steps = [...document.querySelectorAll(".step")];
let currentStep = 1;
let latestAvailability = null;

window.addEventListener("scroll", () => {
  navbar.classList.toggle("scrolled", window.scrollY > 12);
});

const today = new Date();
today.setMinutes(today.getMinutes() - today.getTimezoneOffset());
bookingDateInput.min = today.toISOString().slice(0, 10);

function setStatus(message, type = "info") {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner status-${type}`;
  statusBanner.hidden = !message;
}

function renderSlots(slots = []) {
  timeSlotSelect.innerHTML = '<option value="" disabled selected>Select time slot</option>';
  slots.forEach((slot) => {
    const option = document.createElement("option");
    option.value = slot.time;
    option.disabled = !slot.isAvailable;
    option.textContent = `${slot.time} (${slot.remaining}/${slot.capacity} available)`;
    timeSlotSelect.appendChild(option);
  });
}

async function loadAvailability(dateValue) {
  if (!dateValue) return;
  setStatus("Loading slot availability...", "info");
  try {
    const response = await fetch(`/api/booking/availability?date_value=${encodeURIComponent(dateValue)}`);
    if (!response.ok) throw new Error("Failed to load slots");

    latestAvailability = await response.json();
    if (latestAvailability.blocked) {
      renderSlots([]);
      setStatus("Selected date is blocked. Choose another date.", "error");
      return;
    }

    renderSlots(latestAvailability.slots);
    setStatus("Slots updated.", "success");
  } catch (error) {
    setStatus("Could not load slot availability. Please retry.", "error");
    console.error(error);
  }
}

function showStep(step) {
  currentStep = step;
  steps.forEach((el) => {
    el.hidden = Number(el.dataset.step) !== step;
  });

  backBtn.hidden = step === 1;
  nextBtn.hidden = step === 3;
  submitBtn.hidden = step !== 3;
}

function getPayload() {
  const formData = new FormData(form);
  return {
    vehicle: formData.get("vehicle")?.toString().trim(),
    booking_date: formData.get("bookingDate")?.toString().trim(),
    time_slot: formData.get("timeSlot")?.toString().trim(),
    name: formData.get("name")?.toString().trim(),
    phone: formData.get("phone")?.toString().trim(),
  };
}

function validateStep(step) {
  const payload = getPayload();
  if (step === 1) {
    if (!payload.vehicle || !payload.booking_date || !payload.time_slot) {
      setStatus("Please select package, date, and time slot.", "error");
      return false;
    }
  }
  if (step === 3) {
    if (!payload.name || !payload.phone) {
      setStatus("Please enter name and phone.", "error");
      return false;
    }
  }
  return true;
}

function renderSummary() {
  const payload = getPayload();
  summaryPanel.innerHTML = `
    <p><strong>Package:</strong> ${payload.vehicle}</p>
    <p><strong>Date:</strong> ${payload.booking_date}</p>
    <p><strong>Time Slot:</strong> ${payload.time_slot}</p>
  `;
}

bookingDateInput.addEventListener("change", async (event) => {
  await loadAvailability(event.target.value);
});

nextBtn.addEventListener("click", () => {
  if (!validateStep(currentStep)) return;
  if (currentStep === 1) {
    renderSummary();
    showStep(2);
    return;
  }
  if (currentStep === 2) {
    showStep(3);
  }
});

backBtn.addEventListener("click", () => {
  if (currentStep > 1) showStep(currentStep - 1);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateStep(3)) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "Confirming...";
  const payload = getPayload();

  try {
    await loadAvailability(payload.booking_date);
    const selected = latestAvailability?.slots?.find((s) => s.time === payload.time_slot);
    if (!selected?.isAvailable) {
      throw new Error("Selected slot is no longer available.");
    }

    const response = await fetch("/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Booking failed.");
    }

    setStatus(result.message || "Booking submitted successfully!", "success");
    form.hidden = true;
    successScreen.hidden = false;
  } catch (error) {
    setStatus(error.message || "Something went wrong. Please try again.", "error");
    console.error(error);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Confirm Booking";
  }
});

showStep(1);
