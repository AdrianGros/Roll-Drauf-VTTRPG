/**
 * BookScene - 3D Book Opening Animation
 * Stripped down, test-proven version with explicit logging
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

        console.log('[BookScene] Animating book...');

        // Timeline: Book opens
        gsap.timeline()
            // Book rotates upright (rotateY: -15 → 0)
            .to(book, {
                rotateY: 0,
                duration: 0.8,
                ease: 'power2.out'
            }, 0)

            // Cover flips open (rotateY: 0 → -160)
            .to(bookCover, {
                rotateY: -160,
                duration: 1.2,
                ease: 'power2.inOut'
            }, 0.2)

            // Pages rustle
            .to(bookPages, {
                scaleY: [1, 1.002, 1, 1.002, 1],
                duration: 0.4,
                ease: 'sine.inOut'
            }, 0.8)

            // Login form fades in
            .to(loginContent, {
                opacity: 1,
                pointerEvents: 'auto',
                duration: 0.6,
                ease: 'power2.out'
            }, 1.2)

            .eventCallback('onComplete', () => {
                console.log('[BookScene] Animation complete');
            });
    }
};

console.log('[BookScene] Script loaded');
