const form = document.getElementById("contactForm");
const navbar = document.getElementById("navbar");

window.addEventListener("scroll", () => {
  if (window.scrollY > 12) {
    navbar.classList.add("scrolled");
  } else {
    navbar.classList.remove("scrolled");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = {
    name: formData.get("name")?.toString().trim(),
    phone: formData.get("phone")?.toString().trim(),
    vehicle: formData.get("vehicle")?.toString().trim(),
  };

  if (!payload.name || !payload.phone || !payload.vehicle) {
    alert("Please fill all fields.");
    return;
  }

  try {
    const response = await fetch("/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("Failed to submit booking.");
    }

    const result = await response.json();
    alert(result.message || "Booking submitted successfully!");
    form.reset();
  } catch (error) {
    alert("Something went wrong. Please try again.");
    console.error(error);
  }
});
