document.addEventListener('DOMContentLoaded', () => {
    const categoryTabsWrap = document.getElementById('generalResourceCategoryTabs');
    const searchInput = document.getElementById('resourceSearchInput');
    const kindFilter = document.getElementById('resourceKindFilter');
    const providerFilter = document.getElementById('resourceProviderFilter');
    const featuredOnly = document.getElementById('resourceFeaturedOnly');
    const resetBtn = document.getElementById('resourceFilterReset');
    const countLabel = document.getElementById('resourceFilterCount');
    const emptyState = document.getElementById('resourceFilterEmpty');

    const isGeneralPanelReady = categoryTabsWrap && searchInput && kindFilter && providerFilter && featuredOnly;
    if (!isGeneralPanelReady) {
        return;
    }

    const centerTabInView = (tabButton) => {
        if (!tabButton || !categoryTabsWrap) {
            return;
        }

        const scrollTarget = tabButton.offsetLeft - (categoryTabsWrap.clientWidth / 2) + (tabButton.clientWidth / 2);
        categoryTabsWrap.scrollTo({
            left: Math.max(0, scrollTarget),
            behavior: 'smooth',
        });
    };

    const classifyKind = (text, url) => {
        const corpus = `${text} ${url}`;
        if (/cert|certificate|comptia|pmi/.test(corpus)) {
            return 'certification';
        }
        if (/docs|documentation|developer|guide|reference|manual/.test(corpus)) {
            return 'docs';
        }
        if (/lab|challenge|practice|hands-on|sandbox|ctf/.test(corpus)) {
            return 'practice';
        }
        if (/community|forum|stackoverflow|reddit|discord/.test(corpus)) {
            return 'community';
        }
        if (/learn|course|academy|tutorial|codelab|training|path/.test(corpus)) {
            return 'course';
        }
        return 'course';
    };

    const classifyProvider = (url) => {
        if (/docs\.|developer\.|kubernetes\.io|apache\.org|microsoft\.com|google\.com|apple\.com/.test(url)) {
            return 'official';
        }
        if (/stackoverflow|reddit|forum|community|nngroup/.test(url)) {
            return 'community';
        }
        return 'platform';
    };

    const getActivePane = () => {
        return document.querySelector('#generalResourceCategoryContent .tab-pane.active.show')
            || document.querySelector('#generalResourceCategoryContent .tab-pane.active');
    };

    const applyFilters = () => {
        const activePane = getActivePane();
        if (!activePane) {
            return;
        }

        const query = searchInput.value.trim().toLowerCase();
        const kind = kindFilter.value;
        const provider = providerFilter.value;
        const onlyFeatured = featuredOnly.checked;

        const cards = Array.from(activePane.querySelectorAll('[data-resource-card="1"]'));
        let visibleCount = 0;

        cards.forEach((card) => {
            const text = card.dataset.search || '';
            const href = (card.getAttribute('href') || '').toLowerCase();
            const isFeatured = card.dataset.featured === '1';
            const cardKind = classifyKind(text, href);
            const cardProvider = classifyProvider(href);

            const queryMatch = !query || text.includes(query);
            const kindMatch = kind === 'all' || cardKind === kind;
            const providerMatch = provider === 'all' || cardProvider === provider;
            const featuredMatch = !onlyFeatured || isFeatured;

            const visible = queryMatch && kindMatch && providerMatch && featuredMatch;
            card.classList.toggle('d-none', !visible);

            if (visible) {
                visibleCount += 1;
            }
        });

        countLabel.textContent = `Showing ${visibleCount} resource${visibleCount === 1 ? '' : 's'}`;
        emptyState.classList.toggle('d-none', visibleCount > 0);
    };

    const activeTabButton = categoryTabsWrap.querySelector('.nav-link.active');
    if (activeTabButton) {
        centerTabInView(activeTabButton);
    }

    categoryTabsWrap.querySelectorAll('[data-bs-toggle="tab"]').forEach((tabButton) => {
        tabButton.addEventListener('shown.bs.tab', (event) => {
            centerTabInView(event.target);
            applyFilters();
        });
    });

    searchInput.addEventListener('input', applyFilters);
    kindFilter.addEventListener('change', applyFilters);
    providerFilter.addEventListener('change', applyFilters);
    featuredOnly.addEventListener('change', applyFilters);

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            searchInput.value = '';
            kindFilter.value = 'all';
            providerFilter.value = 'all';
            featuredOnly.checked = false;
            applyFilters();
        });
    }

    applyFilters();
});
