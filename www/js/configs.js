// Copy to clipboard
function copyToClipboard(button) {
  const input = button.previousElementSibling;
  const text = input.value;
  
  navigator.clipboard.writeText(text).then(() => {
    const originalText = button.textContent;
    button.textContent = '✓ Copied!';
    
    setTimeout(() => {
      button.textContent = originalText;
    }, 2000);
  }).catch(err => {
    alert('Failed to copy: ' + err);
  });
}

// Show QR code
function showQR(url) {
  const modal = document.getElementById('qr-modal');
  const qrCode = document.getElementById('qr-code');
  
  // Clear previous QR
  qrCode.innerHTML = '';
  
  // Generate new QR
  new QRCode(qrCode, {
    text: url,
    width: 300,
    height: 300,
    colorDark: '#e4e4e7',
    colorLight: '#1a1b2e'
  });
  
  modal.classList.add('active');
}

// Close QR modal
function closeQR() {
  const modal = document.getElementById('qr-modal');
  modal.classList.remove('active');
}

// Close modal on outside click
document.addEventListener('click', function(e) {
  const modal = document.getElementById('qr-modal');
  if (e.target === modal) {
    modal.classList.remove('active');
  }
});

// Close on ESC
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const modal = document.getElementById('qr-modal');
    modal.classList.remove('active');
  }
});
