/**
 * CDAVP Clean Cross-Platform Core Engine
 * Standard, robust, 100% compatible with Edge, Chrome, Safari, Firefox, iOS, Android
 */

document.addEventListener('DOMContentLoaded', () => {
  initOTPInputController();
  initAutoDismissAlerts();
});

/* ==========================================================================
   1. OTP 6-BOX INPUT CONTROLLER & RESEND TIMER
   ========================================================================== */
function initOTPInputController() {
  const otpContainer = document.querySelector('.otp-container-clean');
  const mainInput = document.querySelector('.otp-main-input');
  if (!otpContainer || !mainInput) return;

  const boxes = otpContainer.querySelectorAll('.otp-digit-input');

  boxes.forEach((box, index) => {
    // Input handling
    box.addEventListener('input', e => {
      const val = e.target.value.replace(/\D/g, '');
      box.value = val ? val.slice(-1) : '';

      if (val && index < boxes.length - 1) {
        boxes[index + 1].focus();
      }

      updateMainOTP();
    });

    // Backspace navigation
    box.addEventListener('keydown', e => {
      if (e.key === 'Backspace' && !box.value && index > 0) {
        boxes[index - 1].focus();
      }
    });

    // Paste handling
    box.addEventListener('paste', e => {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim().replace(/\D/g, '');
      if (pasteData) {
        const digits = pasteData.slice(0, boxes.length).split('');
        digits.forEach((d, i) => {
          if (boxes[i]) boxes[i].value = d;
        });
        const nextIdx = Math.min(digits.length, boxes.length - 1);
        boxes[nextIdx].focus();
        updateMainOTP();
      }
    });
  });

  function updateMainOTP() {
    let full = '';
    boxes.forEach(b => { full += b.value.trim(); });
    mainInput.value = full;
  }

  // Timer logic
  initOTPTimer();
}

function initOTPTimer() {
  const timerDisplay = document.getElementById('otp-timer-display');
  const resendBtn = document.getElementById('otp-resend-btn');
  if (!timerDisplay || !resendBtn) return;

  let timeLeft = 60;
  let timerInterval = null;

  function startCountdown() {
    resendBtn.disabled = true;
    resendBtn.classList.add('disabled');
    timeLeft = 60;

    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      timeLeft--;
      const m = Math.floor(timeLeft / 60);
      const s = timeLeft % 60;
      timerDisplay.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

      if (timeLeft <= 0) {
        clearInterval(timerInterval);
        timerDisplay.textContent = "00:00";
        resendBtn.disabled = false;
        resendBtn.classList.remove('disabled');
      }
    }, 1000);
  }

  startCountdown();

  // Resend OTP AJAX
  resendBtn.addEventListener('click', async e => {
    e.preventDefault();
    if (resendBtn.disabled) return;

    resendBtn.disabled = true;
    resendBtn.textContent = 'Sending...';

    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      const response = await fetch('/accounts/resend-otp/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        }
      });
      const data = await response.json();

      if (data.success) {
        showToast(data.message || 'OTP resent successfully!', 'success');
        const debugBanner = document.getElementById('debug-otp-banner');
        if (debugBanner && data.debug_otp) {
          debugBanner.textContent = data.debug_otp;
        }
        resendBtn.textContent = 'Resend OTP';
        startCountdown();
      } else {
        showToast(data.message || 'Failed to resend OTP', 'danger');
        resendBtn.disabled = false;
        resendBtn.textContent = 'Resend OTP';
      }
    } catch (err) {
      showToast('Error connecting to server. Please try again.', 'danger');
      resendBtn.disabled = false;
      resendBtn.textContent = 'Resend OTP';
    }
  });
}

/* ==========================================================================
   2. ALERTS AUTO-DISMISS & TOAST UTILITY
   ========================================================================== */
function initAutoDismissAlerts() {
  setTimeout(() => {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
      alert.classList.add('fade');
      setTimeout(() => alert.remove(), 400);
    });
  }, 6000);
}

function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText = 'position: fixed; top: 18px; right: 18px; z-index: 1090; display: flex; flex-direction: column; gap: 8px;';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  toast.className = `alert alert-${type} shadow-sm rounded-3 py-2 px-3 border d-flex align-items-center gap-2 mb-0`;
  toast.style.cssText = 'min-width: 260px; font-size: 13px; font-weight: 500;';
  toast.innerHTML = `<span>${message}</span>`;

  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
