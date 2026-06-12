// Constants representing lag and rolling fields
const ALL_LAG_FIELDS = [
  "PM2.5_lag1", "PM2.5_lag2", "PM2.5_lag3", "PM2.5_lag6",
  "PM2.5_lag12", "PM2.5_lag24", "PM2.5_lag48", "PM2.5_lag72",
  "PM2.5_roll3_mean", "PM2.5_roll3_std",
  "PM2.5_roll6_mean",  "PM2.5_roll6_std",
  "PM2.5_roll12_mean", "PM2.5_roll12_std",
  "PM2.5_roll24_mean", "PM2.5_roll24_std",
];

// Helper to show prefill status message
function setPrefillStatus(message, type = '') {
  const statusEl = document.getElementById("prefill-status");
  statusEl.className = "status-msg";
  statusEl.innerHTML = "";
  
  if (!message) return;

  statusEl.classList.add(type);
  if (type === 'loading') {
    statusEl.innerHTML = `<span>⏳</span> ${message}`;
  } else if (type === 'success') {
    statusEl.innerHTML = `<span>✅</span> ${message}`;
  } else if (type === 'error') {
    statusEl.innerHTML = `<span>⚠️</span> ${message}`;
  } else {
    statusEl.innerText = message;
  }
}

// Fetch prefill data from Open-Meteo for the specified city
async function prefillFromOpenMeteo() {
  const cityInput = document.getElementById("city-input");
  const city = cityInput.value.trim();
  
  if (!city) {
    setPrefillStatus("Please enter a city name first.", "error");
    return;
  }

  setPrefillStatus(`Querying Open-Meteo for "${city}"...`, "loading");

  try {
    const response = await fetch(`/prefill/${encodeURIComponent(city)}`);
    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.found) {
      setPrefillStatus(data.warning || `No data found for "${city}".`, "error");
      return;
    }

    // Populate all lag/roll inputs
    ALL_LAG_FIELDS.forEach(field => {
      // Find input by name attribute
      const inputEl = document.querySelector(`[name="${field}"]`);
      if (inputEl && data.lags[field] !== undefined) {
        inputEl.value = parseFloat(data.lags[field]).toFixed(2);
      }
    });

    // Populate current pollutants and meteorological variables
    if (data.current) {
      Object.keys(data.current).forEach(key => {
        const inputEl = document.querySelector(`[name="${key}"]`);
        if (inputEl) {
          if (inputEl.tagName === "SELECT") {
            inputEl.value = data.current[key];
          } else {
            const val = data.current[key];
            inputEl.value = typeof val === "number" ? val.toFixed(1) : val;
          }
        }
      });
    }

    // Automatically expand the details section to show the filled values
    const lagSection = document.getElementById("lag-section");
    if (lagSection) {
      lagSection.open = true;
    }

    // Format timestamp
    let timeStr = "";
    if (data.timestamp) {
      try {
        const date = new Date(data.timestamp);
        timeStr = ` at ${date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} local`;
      } catch (e) {
        timeStr = ` (${data.timestamp})`;
      }
    }

    let msg = `Filled for ${data.city}${timeStr}`;
    if (data.warning) {
      msg += `. Note: ${data.warning}`;
      setPrefillStatus(msg, "error");
    } else {
      setPrefillStatus(msg, "success");
    }
  } catch (error) {
    console.error("Open-Meteo prefill error:", error);
    setPrefillStatus(`Failed to fetch data: ${error.message}`, "error");
  }
}

// Collect data from the form and return a structured object
function collectFormData() {
  const form = document.getElementById("input-form");
  const data = {};
  
  // Find all input and select elements
  const elements = form.querySelectorAll("input, select");
  elements.forEach(el => {
    if (!el.name) return;
    
    if (el.type === "number") {
      // Parse empty inputs as 0 or undefined. Let Pydantic validate.
      const val = parseFloat(el.value);
      data[el.name] = isNaN(val) ? 0.0 : val;
    } else {
      data[el.name] = el.value;
    }
  });

  return data;
}

// Validate form inputs (returns true if valid, false otherwise)
function validateForm() {
  const form = document.getElementById("input-form");
  return form.reportValidity();
}

// Submit data to the prediction API
async function submitPrediction() {
  if (!validateForm()) {
    // Expand sections if required fields are inside collapsed details
    document.querySelectorAll("details").forEach(details => {
      const invalidInput = details.querySelector("input:invalid, select:invalid");
      if (invalidInput) {
        details.open = true;
      }
    });
    return;
  }

  const spinner = document.getElementById("spinner");
  const resultCard = document.getElementById("result-card");
  const standbyCard = document.getElementById("standby-card");
  const errorMsg = document.getElementById("error-msg");

  // Reset UI state
  spinner.hidden = false;
  resultCard.hidden = true;
  standbyCard.hidden = true;
  errorMsg.hidden = true;

  const requestBody = collectFormData();

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || `Server returned HTTP ${response.status}`);
    }

    const result = await response.json();

    // Update result UI elements
    document.getElementById("pm25-value").innerText = result.pm25_predicted.toFixed(1);
    
    const bandTextEl = document.getElementById("aqi-band-text");
    bandTextEl.innerText = result.aqi_band;

    // Apply dynamic colors to the AQI badge
    const badge = document.getElementById("aqi-badge");
    badge.style.setProperty("--badge-bg", `${result.color}18`);
    badge.style.setProperty("--badge-border", result.color);
    badge.style.setProperty("--badge-glow", `${result.color}33`);
    badge.style.color = result.color;

    // Apply color border to the card
    resultCard.style.setProperty("--border-color", result.color);

    // Update safety indicators
    const safetyIcon = document.getElementById("safety-icon");
    const safetyTitle = document.getElementById("safety-title");
    const safetyText = document.getElementById("safe-outside");
    const safetyCard = document.getElementById("safety-card");

    if (result.safe_outside === true) {
      safetyIcon.innerText = "✅";
      safetyTitle.innerText = "Air Quality is Safe";
      safetyText.innerText = "Conditions are perfect for outdoor exercise and activities.";
      safetyCard.style.borderLeft = "4px solid #00e676";
    } else if (result.safe_outside === false) {
      safetyIcon.innerText = "❌";
      safetyTitle.innerText = "Unsafe Outdoors";
      safetyText.innerText = "Air quality is hazardous. Stay indoors or wear protective gear.";
      safetyCard.style.borderLeft = "4px solid #ff1744";
    } else {
      safetyIcon.innerText = "⚠️";
      safetyTitle.innerText = "Caution Advised";
      safetyText.innerText = "Sensitive individuals should limit prolonged outdoor exposure.";
      safetyCard.style.borderLeft = "4px solid #ffd600";
    }

    // Update health advisory
    document.getElementById("advice-text").innerText = result.advice;

    // Show result card
    resultCard.hidden = false;
  } catch (error) {
    console.error("Prediction failed:", error);
    document.getElementById("error-text").innerText = error.message;
    errorMsg.hidden = false;
  } finally {
    spinner.hidden = true;
  }
}

// Setup dates and event listeners on load
document.addEventListener("DOMContentLoaded", () => {
  // Set current datetime values
  const now = new Date();
  
  const hourEl = document.getElementById("hour");
  const dayEl = document.getElementById("day");
  const monthEl = document.getElementById("month");
  
  if (hourEl) hourEl.value = now.getHours();
  if (dayEl) {
    // JS: Sun=0, Mon=1... -> Model: Mon=0, Tue=1... Sun=6
    const jsDay = now.getDay();
    const modelDay = jsDay === 0 ? 6 : jsDay - 1;
    dayEl.value = modelDay;
  }
  if (monthEl) monthEl.value = now.getMonth() + 1;

  // Add event listeners
  const prefillBtn = document.getElementById("prefill-btn");
  if (prefillBtn) {
    prefillBtn.addEventListener("click", prefillFromOpenMeteo);
  }

  const predictBtn = document.getElementById("predict-btn");
  if (predictBtn) {
    predictBtn.addEventListener("click", submitPrediction);
  }
  
  // Also allow pressing enter in city prefill
  const cityInput = document.getElementById("city-input");
  if (cityInput) {
    cityInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        prefillFromOpenMeteo();
      }
    });
  }
});
