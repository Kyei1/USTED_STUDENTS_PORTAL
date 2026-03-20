(function () {
    var sidebar = document.getElementById('studentSidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var openBtn = document.getElementById('sidebarOpenBtn');
    var closeBtn = document.getElementById('sidebarCloseBtn');

    var profileWrap = document.getElementById('profileDropdownWrap');
    var profileBtn = document.getElementById('profileDropdownBtn');
    var profileMenu = document.getElementById('profileDropdownMenu');

    var recordsBtn = document.getElementById('recordsToggleBtn');
    var recordsBody = document.getElementById('recordsPanelBody');
    var recordsHint = document.getElementById('recordsHint');
    var recordsIcon = document.getElementById('recordsLockIcon');

    function openSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.add('show');
        overlay.classList.add('show');
    }

    function closeSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
    }

    if (openBtn) openBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    if (profileBtn && profileMenu) {
        profileBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            profileMenu.classList.toggle('show');
        });

        document.addEventListener('click', function (event) {
            if (!profileWrap || !profileMenu.classList.contains('show')) return;
            if (!profileWrap.contains(event.target)) {
                profileMenu.classList.remove('show');
            }
        });
    }

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
