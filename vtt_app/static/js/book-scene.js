/**
 * BookScene - 3D Book Opening & Page Turn Navigation
 * Handles immersive book-based UI transitions using GSAP 3D transforms
 */

window.BookScene = {
    isInitialized: false,
    isAnimating: false,
    timeline: null,

    /**
     * Create the 3D book HTML structure and inject into DOM
     */
    create() {
        if (this.isInitialized) return;

        const bookHTML = `
            <div id="book-scene-wrapper">
                <div id="book">
                    <!-- Front cover -->
                    <div class="book-element book-cover">
                        <div class="cover-title">Spellbook</div>
                        <div class="cover-ornament">✨</div>
                    </div>

                    <!-- Spine pages (visual stack) -->
                    <div class="book-element book-pages"></div>

                    <!-- Back cover -->
                    <div class="book-element book-back"></div>

                    <!-- Content that appears inside open book -->
                    <div class="book-element book-open-page"></div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('afterbegin', bookHTML);
        this.isInitialized = true;
    },

    /**
     * Animate book opening - reveals login/dashboard content
     * Timeline sequence:
     *  - Book rights rotation (0.6s)
     *  - Front cover flips open (1.0s)
     *  - Pages rustle/shake (0.4s)
     *  - Content fades in (0.6s)
     */
    open(options = {}) {
        if (!this.isInitialized || this.isAnimating) return;

        this.isAnimating = true;
        const duration = options.duration || 1.5; // seconds (not milliseconds)

        // Kill existing timeline if any
        if (this.timeline) this.timeline.kill();

        this.timeline = gsap.timeline({
            onComplete: () => {
                this.isAnimating = false;
                if (options.onComplete) options.onComplete();
            }
        });

        const book = document.getElementById('book');
        const bookCover = document.querySelector('.book-cover');
        const bookPages = document.querySelector('.book-pages');
        const loginContent = document.getElementById('login-content');

        // Phase 1: Adjust book angle (0.6s, starts at t=0)
        // From slightly closed (rotateY -15°) to open angle (rotateY -5°)
        this.timeline.to(
            book,
            {
                rotateY: -5,
                duration: 0.6,
                ease: 'power2.out'
            },
            0
        );

        // Phase 2: Cover flips open (1.0s, starts at t=0.2)
        // From front-facing (rotateY 0°) to fully open (rotateY -150°)
        this.timeline.to(
            bookCover,
            {
                rotateY: -150,
                duration: 1.0,
                ease: 'power2.inOut'
            },
            0.2
        );

        // Phase 3: Pages rustle (0.4s, starts at t=0.8)
        // Subtle scale animation simulating page movement
        this.timeline.to(
            bookPages,
            {
                scaleY: [1, 1.002, 1, 1.002, 1],
                duration: 0.4,
                ease: 'sine.inOut'
            },
            0.8
        );

        // Phase 4: Content fade-in (0.6s, starts at t=1.2)
        // Login form or content becomes visible
        if (loginContent) {
            this.timeline.to(
                loginContent,
                {
                    opacity: 1,
                    duration: 0.6,
                    ease: 'power2.out'
                },
                1.2
            );
        }

        // Also fade out the book scene overlay
        const bookSceneWrapper = document.getElementById('book-scene-wrapper');
        if (bookSceneWrapper) {
            this.timeline.to(
                bookSceneWrapper,
                {
                    opacity: 1,
                    duration: 0
                },
                0
            );
        }
    },

    /**
     * Close the book and hide content (reverse animation)
     * Used when user logs in or navigates away
     */
    close(options = {}) {
        if (!this.isInitialized || this.isAnimating) return;

        this.isAnimating = true;

        if (this.timeline) this.timeline.kill();

        this.timeline = gsap.timeline({
            onComplete: () => {
                this.isAnimating = false;
                if (options.onComplete) options.onComplete();
            }
        });

        const book = document.getElementById('book');
        const bookCover = document.querySelector('.book-cover');
        const loginContent = document.getElementById('login-content');

        // Fade out content (0.3s)
        if (loginContent) {
            this.timeline.to(loginContent, { opacity: 0, duration: 0.3 }, 0);
        }

        // Cover closes (0.6s)
        this.timeline.to(
            bookCover,
            {
                rotateY: 0,
                duration: 0.6,
                ease: 'power2.inOut'
            },
            0
        );

        // Book rotates back (0.6s)
        this.timeline.to(
            book,
            {
                rotateY: -15,
                duration: 0.6,
                ease: 'power2.out'
            },
            0
        );
    },

    /**
     * Page turn transition - animates page flip and navigates to new URL
     * Creates overlay with 3D rotation effect simulating page turn
     * Navigation occurs at 90° (invisible point) for seamless transition
     */
    pageTurn(url) {
        if (this.isAnimating) return;

        this.isAnimating = true;

        // Create page-turn overlay if it doesn't exist
        let overlay = document.querySelector('.page-turn-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'page-turn-overlay';
            document.body.appendChild(overlay);
        }

        // Kill existing timeline
        if (this.timeline) this.timeline.kill();

        this.timeline = gsap.timeline({
            onComplete: () => {
                this.isAnimating = false;
            }
        });

        // Rotate overlay from 0° to -180° (full page turn)
        let navigationTriggered = false;

        this.timeline.to(
            overlay,
            {
                rotateY: -180,
                duration: 0.8,
                ease: 'power2.inOut',
                onUpdate: () => {
                    // Trigger navigation at 90° (midpoint, page is perpendicular/invisible)
                    const progress = this.timeline.progress();
                    if (progress >= 0.5 && !navigationTriggered) {
                        navigationTriggered = true;
                        window.location.href = url;
                    }
                }
            },
            0
        );

        // Fade out overlay after navigation
        this.timeline.to(
            overlay,
            {
                opacity: 0,
                duration: 0.3
            },
            0.7
        );
    }
};

// Ensure GSAP is available
if (typeof gsap === 'undefined') {
    console.warn('BookScene: GSAP library not loaded. 3D animations will be unavailable.');
}
