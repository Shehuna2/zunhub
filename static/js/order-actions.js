// public static file: /static/js/order-actions.js
console.log("order-actions.js loaded");

function toast(message, color) {
  Toastify({
    text: message,
    duration: 3000,
    gravity: 'top',
    position: 'right',
    backgroundColor: color,
    stopOnFocus: true
  }).showToast();
}

function toggleSpinner(show) {
  const spinner = document.getElementById('spinnerOverlay');
  if (spinner) spinner.classList.toggle('hidden', !show);
}

function showModal(modal, content) {
  modal.classList.remove('hidden');
  setTimeout(() => {
    content.classList.remove('opacity-0', 'scale-95');
    content.classList.add('opacity-100', 'scale-100');
  }, 10);
}

function hideModal(modal, content) {
  content.classList.add('opacity-0', 'scale-95');
  content.classList.remove('opacity-100', 'scale-100');
  setTimeout(() => modal.classList.add('hidden'), 200);
}

window.handleOrderAction = function ({
  csrfToken,
  triggerBtnId,
  modalId,
  contentId,
  cancelBtnId,
  confirmBtnId,
  endpoint,
  successMessage,
  btnSuccessText,
  audit
}) {
  const triggerBtn = document.getElementById(triggerBtnId);
  const modal      = document.getElementById(modalId);
  const content    = document.getElementById(contentId);
  const cancelBtn  = document.getElementById(cancelBtnId);
  const confirmBtn = document.getElementById(confirmBtnId);

  if (!triggerBtn || !modal || !content || !cancelBtn || !confirmBtn) {
    console.warn('❌ Missing DOM elements for action binding:', triggerBtnId);
    return;
  }

  console.log("🔁 handleOrderAction attached to", triggerBtnId);

  triggerBtn.addEventListener('click', () => {
    console.log('Button clicked:', triggerBtnId);

    showModal(modal, content);

    cancelBtn.addEventListener('click', () => hideModal(modal, content));

    confirmBtn.addEventListener('click', async () => {
      confirmBtn.disabled = true;
      toggleSpinner(true);

      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Accept': 'application/json'
          },
        });

        if (res.ok) {
          const data = await res.json();

          // 1) Let the server‐rendered partials update status & buttons
          if (typeof fetchAndReplaceOrderBlocks === 'function') {
            await fetchAndReplaceOrderBlocks();
          }

          // 2) Then show the toast
          toast(data.message || successMessage, 'linear-gradient(to right, #00b09b, #96c93d)');

          // 3) Finally, cosmetically disable this button
          triggerBtn.textContent = btnSuccessText;
          triggerBtn.disabled    = true;
          triggerBtn.classList.add('bg-gray-500');

          if (audit) {
            navigator.sendBeacon('/api/log/', JSON.stringify({
              action: audit,
              endpoint,
              timestamp: new Date().toISOString()
            }));
          }
        } else {
          const error = await res.text();
          toast('Error: ' + error, 'linear-gradient(to right, #e52d27, #b31217)');
        }
      } catch (err) {
        toast('Request failed: ' + err.message, 'linear-gradient(to right, #e52d27, #b31217)');
      } finally {
        confirmBtn.disabled = false;
        hideModal(modal, content);
        toggleSpinner(false);
      }
    }); // End confirmBtn click
  }); // End triggerBtn click
}; // End handleOrderAction
