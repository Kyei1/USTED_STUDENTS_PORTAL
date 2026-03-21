(function () {
    var recordsBtn = document.getElementById('recordsToggleBtn');
    var recordsBody = document.getElementById('recordsPanelBody');
    var recordsHint = document.getElementById('recordsHint');
    var recordsIcon = document.getElementById('recordsLockIcon');

    if (recordsBtn && recordsBody && recordsHint && recordsIcon) {
        recordsBtn.addEventListener('click', function () {
            var isHidden = recordsBody.classList.contains('d-none');
            recordsBody.classList.toggle('d-none');

            if (isHidden) {
                recordsBtn.innerHTML = '<i class="bi bi-eye-slash-fill me-1"></i> Hide Results';
                recordsHint.textContent = 'You can hide your academic standing again anytime.';
                recordsIcon.className = 'bi bi-mortarboard-fill fs-4';
                recordsIcon.style.color = 'var(--usted-maroon)';
            } else {
                recordsBtn.innerHTML = '<i class="bi bi-eye-fill me-1"></i> Reveal Current Academic Standing';
                recordsHint.textContent = 'For your privacy, this section is hidden by default.';
                recordsIcon.className = 'bi bi-lock-fill fs-4';
                recordsIcon.style.color = 'var(--usted-text-muted)';
            }
        });
    }
})();
