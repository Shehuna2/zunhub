// order-actions.js
window.handleOrderAction = function(config) {
  const {
      csrfToken,
      triggerBtnId,
      modalId,
      contentId,
      cancelBtnId,
      confirmBtnId,
      endpoint,
      successMessage,
      statusText,
      statusColor,
      btnSuccessText,
      audit
  } = config;

  const triggerBtn = document.getElementById(triggerBtnId);
  const modal = document.getElementById(modalId);
  const modalContent = document.getElementById(contentId);
  const cancelBtn = document.getElementById(cancelBtnId);
  const confirmBtn = document.getElementById(confirmBtnId);

  // Check if elements exist
  if (!triggerBtn || !modal || !modalContent || !cancelBtn || !confirmBtn) {
      console.error(`Missing elements for ${triggerBtnId}:`, { triggerBtn, modal, modalContent, cancelBtn, confirmBtn });
      return;
  }

  // Show modal on button click
  triggerBtn.addEventListener('click', () => {
      modal.classList.remove('hidden');
      modalContent.classList.remove('scale-95', 'opacity-0');
      modalContent.classList.add('scale-100', 'opacity-100');
  });

  // Hide modal on cancel
  cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
      modalContent.classList.add('scale-95', 'opacity-0');
      modalContent.classList.remove('scale-100', 'opacity-100');
  });

  // Handle confirm action
  confirmBtn.addEventListener('click', () => {
      // Show spinner
      const spinner = document.getElementById('spinnerOverlay');
      if (spinner) spinner.classList.remove('hidden');

      fetch(endpoint, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken,
              'X-Requested-With': 'XMLHttpRequest'
          }
      })
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              // Hide modal
              modal.classList.add('hidden');
              modalContent.classList.add('scale-95', 'opacity-0');
              modalContent.classList.remove('scale-100', 'opacity-100');
              // Show success toast
              Toastify({
                  text: successMessage,
                  duration: 3000,
                  gravity: 'top',
                  position: 'right',
                  backgroundColor: '#10B981'
              }).showToast();
              // UI will update via WebSocket
          } else {
              Toastify({
                  text: data.error || 'Action failed',
                  duration: 3000,
                  gravity: 'top',
                  position: 'right',
                  backgroundColor: '#EF4444'
              }).showToast();
          }
      })
      .catch(error => {
          console.error('Error:', error);
          Toastify({
              text: 'An error occurred',
              duration: 3000,
              gravity: 'top',
              position: 'right',
              backgroundColor: '#EF4444'
          }).showToast();
      })
      .finally(() => {
          if (spinner) spinner.classList.add('hidden');
      });
  });
};