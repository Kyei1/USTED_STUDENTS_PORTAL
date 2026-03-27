(function () {
    var menu = document.getElementById('navMenu');
    var toggle = document.getElementById('menuToggle');
    var profileWrap = document.getElementById('topProfileWrap');
    var profileBtn = document.getElementById('topProfileBtn');
    var profileMenu = document.getElementById('topProfileMenu');
    var notifyWrap = document.getElementById('topNotifyWrap');
    var notifyBtn = document.getElementById('topNotifyBtn');
    var notifyMenu = document.getElementById('topNotifyMenu');
    var notifyBadge = document.getElementById('topNotifyBadge');
    var studentSidebarOpenBtn = document.getElementById('studentSidebarOpenBtn');
    var studentSidebarCloseBtn = document.getElementById('studentSidebarCloseBtn');
    var studentSidebar = document.getElementById('studentSidebar');
    var studentOverlay = document.getElementById('studentSidebarOverlay');

    function closeStudentSidebar() {
        if (!studentSidebar || !studentOverlay) {
            return;
        }
        studentSidebar.classList.remove('show');
        studentOverlay.classList.remove('show');
        if (studentSidebarOpenBtn) {
            studentSidebarOpenBtn.setAttribute('aria-expanded', 'false');
        }
    }

    function openStudentSidebar() {
        if (!studentSidebar || !studentOverlay) {
            return;
        }
        studentSidebar.classList.add('show');
        studentOverlay.classList.add('show');
        if (studentSidebarOpenBtn) {
            studentSidebarOpenBtn.setAttribute('aria-expanded', 'true');
        }
    }

    function markTopAnnouncementsRead() {
        if (!notifyMenu || notifyMenu.dataset.readSync === 'done') {
            return;
        }

        fetch('/announcements/mark-read', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(function () {
            notifyMenu.dataset.readSync = 'done';
            if (notifyBadge) {
                notifyBadge.remove();
            }
            notifyMenu.querySelectorAll('.notify-item.notify-unread').forEach(function (node) {
                node.classList.remove('notify-unread');
            });
        }).catch(function () {
            // Keep UI usable even if the read endpoint fails.
        });
    }

    if (menu && toggle) {
        toggle.addEventListener('click', function () {
            var isOpen = menu.classList.toggle('show');
            toggle.setAttribute('aria-expanded', String(isOpen));
        });
    }

    if (profileBtn && profileMenu) {
        profileBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            profileMenu.classList.toggle('show');
            if (notifyMenu) {
                notifyMenu.classList.remove('show');
            }
        });

        document.addEventListener('click', function (event) {
            if (!profileWrap || !profileMenu.classList.contains('show')) {
                return;
            }
            if (!profileWrap.contains(event.target)) {
                profileMenu.classList.remove('show');
            }
        });
    }

    if (notifyBtn && notifyMenu) {
        notifyBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            notifyMenu.classList.toggle('show');
            if (profileMenu) {
                profileMenu.classList.remove('show');
            }
            if (notifyMenu.classList.contains('show')) {
                markTopAnnouncementsRead();
            }
        });

        document.addEventListener('click', function (event) {
            if (!notifyWrap || !notifyMenu.classList.contains('show')) {
                return;
            }
            if (!notifyWrap.contains(event.target)) {
                notifyMenu.classList.remove('show');
            }
        });
    }

    if (studentSidebarOpenBtn) {
        studentSidebarOpenBtn.addEventListener('click', function () {
            openStudentSidebar();
        });
    }

    if (studentSidebarCloseBtn) {
        studentSidebarCloseBtn.addEventListener('click', function () {
            closeStudentSidebar();
        });
    }

    if (studentOverlay) {
        studentOverlay.addEventListener('click', function () {
            closeStudentSidebar();
        });
    }
})();
