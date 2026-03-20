(function () {
    var menu = document.getElementById('navMenu');
    var toggle = document.getElementById('menuToggle');
    var profileWrap = document.getElementById('topProfileWrap');
    var profileBtn = document.getElementById('topProfileBtn');
    var profileMenu = document.getElementById('topProfileMenu');

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
})();
