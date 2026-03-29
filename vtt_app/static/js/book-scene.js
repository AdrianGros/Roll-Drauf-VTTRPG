/**
 * BookScene - 3D Book Opening Animation
 * Fixed GSAP camelCase property names (rotationY not rotateY)
 * Based on GSAP docs: https://gsap.com/docs/v3/GSAP/CorePlugins/CSS/
 */

window.BookScene = {
    isOpened: false,

    create() {
        console.log('[BookScene] Creating book HTML...');

        const bookHTML = `
            <div id="book-scene-wrapper">
                <div id="book">
                    <div class="book-element book-cover">
                        <div class="cover-title">Spellbook</div>
                        <div class="cover-ornament">✨</div>
                    </div>
                    <div class="book-element book-pages"></div>
                    <div class="book-element book-back"></div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('afterbegin', bookHTML);
        console.log('[BookScene] Book HTML injected');

        // Click handler for manual open
        document.addEventListener('click', (e) => {
            if (e.target.closest('.book-cover') && !this.isOpened) {
                console.log('[BookScene] Book clicked, opening...');
                this.open();
            }
        });
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
    }
};

console.log('[BookScene] ✓ Script loaded and BookScene object created');
