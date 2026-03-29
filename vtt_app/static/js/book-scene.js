/**
 * BookScene - 3D Book Opening Animation
 * Fixed GSAP camelCase property names (rotationY not rotateY)
 * Based on GSAP docs: https://gsap.com/docs/v3/GSAP/CorePlugins/CSS/
 */

window.BookScene = {
    isOpened: false,
    currentPage: 'dashboard',  // Track current page for keyboard navigation
    navigationMap: {
        'dashboard': { prev: null, next: '/campaigns' },
        'campaigns': { prev: '/dashboard', next: '/characters' },
        'characters': { prev: '/campaigns', next: null },
        // Add more pages as needed
    },

    create() {
        console.log('[BookScene] Creating book HTML...');

        const bookHTML = `
            <div id="book-scene-wrapper" role="region" aria-label="Spellbook application interface">
                <div id="book" role="doc-cover" aria-label="Interactive spellbook">
                    <div class="book-element book-cover" role="button" tabindex="0" aria-label="Book front cover - press Enter or click to open" aria-pressed="false">
                        <div class="cover-title" aria-hidden="false">Spellbook</div>
                        <div class="cover-ornament" aria-hidden="true">✨</div>
                    </div>
                    <div class="book-element book-pages" role="doc-pagebreak" aria-label="Book pages"></div>
                    <div class="book-element book-back" role="doc-cover" aria-label="Book back cover"></div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('afterbegin', bookHTML);
        console.log('[BookScene] Book HTML injected');

        // Create and inject bookmark element
        const bookmarkHTML = '<div class="bookmark dashboard"></div>';
        document.body.insertAdjacentHTML('beforeend', bookmarkHTML);
        console.log('[BookScene] Bookmark injected');

        // Click and keyboard handler for manual open
        document.addEventListener('click', (e) => {
            if (e.target.closest('.book-cover') && !this.isOpened) {
                console.log('[BookScene] Book clicked, opening...');
                this.open();
            }
        });

        // Keyboard handler for book cover (Enter or Space)
        document.addEventListener('keydown', (e) => {
            const cover = e.target.closest('.book-cover');
            if (cover && !this.isOpened && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                console.log('[BookScene] Book cover activated via keyboard, opening...');
                this.open();
            }
        });

        // Keyboard navigation (when book is open)
        document.addEventListener('keydown', (e) => {
            if (!this.isOpened) return;  // Only when book is open

            // Prevent navigation if user is typing in a form
            const activeElement = document.activeElement;
            const isFormElement = activeElement.tagName === 'INPUT' ||
                                activeElement.tagName === 'TEXTAREA' ||
                                activeElement.tagName === 'SELECT';
            if (isFormElement && e.key !== 'Escape') return;

            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    const prevPage = this.navigationMap[this.currentPage]?.prev;
                    if (prevPage) {
                        console.log('[BookScene] Keyboard: Navigate to previous page');
                        this.pageTurn(prevPage);
                    }
                    break;

                case 'ArrowRight':
                    e.preventDefault();
                    const nextPage = this.navigationMap[this.currentPage]?.next;
                    if (nextPage) {
                        console.log('[BookScene] Keyboard: Navigate to next page');
                        this.pageTurn(nextPage);
                    }
                    break;

                case 'Escape':
                    e.preventDefault();
                    // Return to dashboard
                    if (this.currentPage !== 'dashboard') {
                        console.log('[BookScene] Keyboard: Return to dashboard (ESC)');
                        this.pageTurn('/dashboard');
                    }
                    break;
            }
        });

        console.log('[BookScene] Keyboard navigation initialized');
    },

    open() {
        if (this.isOpened) {
            console.log('[BookScene] Book already opened');
            return;
        }

        console.log('[BookScene] open() called');

        if (typeof gsap === 'undefined') {
            console.error('[BookScene] GSAP not available! Retrying in 100ms...');
            setTimeout(() => this.open(), 100);
            return;
        }

        console.log('[BookScene] GSAP available, starting animation');
        this.isOpened = true;

        const book = document.getElementById('book');
        const bookCover = document.querySelector('.book-cover');
        const bookPages = document.querySelector('.book-pages');
        const loginContent = document.getElementById('login-content');

        if (!book || !bookCover) {
            console.error('[BookScene] Book elements not found in DOM');
            return;
        }

        console.log('[BookScene] Found all elements, building timeline...');

        // Create timeline with proper GSAP syntax
        const timeline = gsap.timeline();

        console.log('[BookScene] Adding animations to timeline...');

        // Phase 1: Book rotates upright (rotationY not rotateY!)
        // -15° → 0° (front-facing)
        timeline.to(book, {
            rotationY: 0,
            duration: 0.8,
            ease: 'power2.out',
            force3D: true
        }, 0);

        console.log('[BookScene] → Book rotation added (rotationY: 0)');

        // Phase 2: Cover flips open (0° → -160°)
        timeline.to(bookCover, {
            rotationY: -160,
            duration: 1.2,
            ease: 'power2.inOut',
            force3D: true
        }, 0.2);

        console.log('[BookScene] → Cover flip added (rotationY: -160)');

        // Phase 3: Pages rustle effect
        timeline.to(bookPages, {
            scaleY: [1, 1.002, 1, 1.002, 1],
            duration: 0.4,
            ease: 'sine.inOut',
            force3D: true
        }, 0.8);

        console.log('[BookScene] → Pages rustle added');

        // Phase 4: Login form fades in
        timeline.to(loginContent, {
            opacity: 1,
            pointerEvents: 'auto',
            duration: 0.6,
            ease: 'power2.out'
        }, 1.2);

        console.log('[BookScene] → Login content fade-in added');

        timeline.eventCallback('onStart', () => {
            console.log('[BookScene] ▶ Animation STARTED');
        });

        timeline.eventCallback('onUpdate', () => {
            console.log('[BookScene] ⏱ Progress:', Math.round(timeline.progress() * 100) + '%');
        });

        timeline.eventCallback('onComplete', () => {
            console.log('[BookScene] ✅ Animation COMPLETE');
        });

        console.log('[BookScene] 🎬 Timeline built and ready to play');
    },

    pageTurn(url) {
        console.log('[BookScene] pageTurn() called, destination:', url);

        if (!this.isOpened) {
            console.warn('[BookScene] Book not opened, falling back to direct navigation');
            window.location.href = url;
            return;
        }

        if (typeof gsap === 'undefined') {
            console.error('[BookScene] GSAP not available for page turn, falling back to direct navigation');
            window.location.href = url;
            return;
        }

        // Create page-turn overlay if it doesn't exist
        let overlay = document.querySelector('.page-turn-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'page-turn-overlay';
            document.body.appendChild(overlay);
            console.log('[BookScene] Created page-turn overlay');
        }

        // Ensure overlay is visible and ready
        overlay.style.opacity = '1';
        overlay.style.pointerEvents = 'auto';
        overlay.style.transform = 'perspective(2000px) rotateY(0deg)';

        // Prevent interaction during animation
        document.body.style.overflow = 'hidden';

        // Create page-turn timeline
        const timeline = gsap.timeline();

        console.log('[BookScene] Building page-turn timeline...');

        // Animate page rotation: 0° → -180° (full 180° rotation over 0.6s)
        timeline.to(overlay, {
            rotationY: -180,
            duration: 0.6,
            ease: 'power2.inOut',
            force3D: true
        }, 0);

        // At midpoint (t=0.3s, 90° rotation), navigate to new page
        // At this point the overlay is perpendicular to screen (invisible)
        timeline.add(() => {
            console.log('[BookScene] Navigating to:', url);
            // Update bookmark before navigation (visual continuity)
            this.updateBookmarkPosition(url);
            window.location.href = url;
        }, 0.3);

        // Callback on complete (may not reach if page navigation occurs)
        timeline.eventCallback('onComplete', () => {
            console.log('[BookScene] Page turn animation complete');
            // Reset for potential future animations
            overlay.style.opacity = '0';
            overlay.style.pointerEvents = 'none';
            document.body.style.overflow = 'auto';
        });

        console.log('[BookScene] Page turn timeline ready, duration: 0.6s');
    },

    updateCurrentPage() {
        // Derive current page from URL pathname
        const pathname = window.location.pathname;

        if (pathname.includes('/campaigns')) {
            this.currentPage = 'campaigns';
        } else if (pathname.includes('/characters')) {
            this.currentPage = 'characters';
        } else if (pathname.includes('/dashboard') || pathname === '/') {
            this.currentPage = 'dashboard';
        } else {
            this.currentPage = pathname;  // Use pathname as-is if not recognized
        }

        console.log('[BookScene] Current page:', this.currentPage);

        // Update bookmark position
        this.updateBookmarkPosition();
    },

    updateBookmarkPosition(url = null) {
        const bookmark = document.querySelector('.bookmark');
        if (!bookmark) return;

        // Determine target page from URL or current page
        let targetPage = this.currentPage;
        if (url) {
            if (url.includes('/campaigns')) targetPage = 'campaigns';
            else if (url.includes('/characters')) targetPage = 'characters';
            else if (url.includes('/dashboard')) targetPage = 'dashboard';
        }

        // Remove all position classes
        bookmark.classList.remove('dashboard', 'campaigns', 'characters');
        // Add new position class
        bookmark.classList.add(targetPage);

        console.log('[BookScene] Bookmark updated to:', targetPage);
    },

    addPageNumbers(pageNumber) {
        // Add page number element to the bottom center of main content
        // pageNumber: number or string (e.g., '1', '3-4' for 2-page spread)

        // Check if page number already exists
        const existing = document.querySelector('.page-number');
        if (existing) {
            existing.textContent = pageNumber;
            return;
        }

        // Create page number element
        const pageNumEl = document.createElement('div');
        pageNumEl.className = 'page-number';
        pageNumEl.textContent = pageNumber;
        pageNumEl.setAttribute('aria-hidden', 'true');  // Hide from screen readers

        // Append to main content area
        const main = document.querySelector('main') || document.body;
        main.appendChild(pageNumEl);

        console.log('[BookScene] Page number added:', pageNumber);
    }
};

// Auto-update current page when script loads
window.BookScene.updateCurrentPage();

console.log('[BookScene] ✓ Script loaded and BookScene object created');
