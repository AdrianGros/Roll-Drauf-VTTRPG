/**
 * M46: Book Opening Animation
 * Creates the magical spellbook opening effect on successful login
 */

(function() {
    'use strict';

    // Check if GSAP is available, provide fallback if not
    const hasGSAP = typeof gsap !== 'undefined';

    /**
     * Create particle (sparkle) element for animation
     */
    function createParticle(x, y) {
        const particle = document.createElement('div');
        particle.className = 'sparkle-particle';
        particle.innerHTML = '✨';
        particle.style.position = 'fixed';
        particle.style.left = x + 'px';
        particle.style.top = y + 'px';
        particle.style.fontSize = '20px';
        particle.style.zIndex = '9999';
        particle.style.pointerEvents = 'none';
        particle.style.opacity = '0';
        document.body.appendChild(particle);
        return particle;
    }

    /**
     * Create book icon element
     */
    function createBookIcon() {
        const book = document.createElement('div');
        book.id = 'spellbook-opening-icon';
        book.innerHTML = '📖';
        book.style.position = 'fixed';
        book.style.top = '50%';
        book.style.left = '50%';
        book.style.transform = 'translate(-50%, -50%)';
        book.style.fontSize = '80px';
        book.style.zIndex = '9998';
        book.style.fontWeight = 'bold';
        book.style.textShadow = '0 0 20px rgba(212, 175, 55, 0.5)';
        book.style.perspective = '1000px';
        document.body.appendChild(book);
        return book;
    }

    /**
     * Animate using GSAP if available, with simple CSS fallback
     */
    function animateWithGSAP(book, particles) {
        const timeline = gsap.timeline();

        // Animate particles
        particles.forEach((particle, index) => {
            timeline.to(particle, {
                opacity: 1,
                x: (Math.random() - 0.5) * 300,
                y: (Math.random() - 0.5) * 300,
                duration: 0.5
            }, 0);

            timeline.to(particle, {
                opacity: 0,
                duration: 0.8
            }, 0.7);
        });

        // Book rotation (main animation)
        timeline.to(book, {
            rotationY: 180,
            duration: 2.0,
            ease: 'power2.inOut'
        }, 0.2);

        // Fade out book
        timeline.to(book, {
            opacity: 0,
            duration: 0.3
        }, 2.0);

        return timeline;
    }

    /**
     * Fallback animation using CSS and setTimeout
     */
    function animateWithCSS(book, particles) {
        const duration = 2500; // ms

        // Add CSS animation styles
        if (!document.getElementById('book-animation-styles')) {
            const style = document.createElement('style');
            style.id = 'book-animation-styles';
            style.innerHTML = `
                @keyframes bookRotate {
                    0% { transform: perspective(1000px) rotateY(0deg); opacity: 1; }
                    50% { transform: perspective(1000px) rotateY(90deg); }
                    100% { transform: perspective(1000px) rotateY(180deg); opacity: 0; }
                }

                @keyframes sparkleFloat {
                    0% { opacity: 1; transform: translate(0, 0); }
                    100% { opacity: 0; transform: translate(var(--tx), var(--ty)); }
                }

                #spellbook-opening-icon {
                    animation: bookRotate 2s ease-in-out forwards;
                    animation-delay: 0.2s;
                }

                .sparkle-particle {
                    animation: sparkleFloat 1.2s ease-out forwards !important;
                }
            `;
            document.head.appendChild(style);
        }

        // Animate each particle with random direction
        particles.forEach((particle, index) => {
            const tx = (Math.random() - 0.5) * 300;
            const ty = (Math.random() - 0.5) * 300;
            particle.style.setProperty('--tx', tx + 'px');
            particle.style.setProperty('--ty', ty + 'px');
            particle.style.animationDelay = index * 0.1 + 's';
        });

        // Return a promise that resolves when animation completes
        return new Promise((resolve) => {
            setTimeout(resolve, duration + 500);
        });
    }

    /**
     * Main book opening animation function
     * Called after successful registration/login
     */
    window.animateBookOpen = async function(options) {
        options = options || {};
        const duration = options.duration || 2.5;
        const particleCount = options.particleCount || 12;

        // Create overlay to prevent interaction
        const overlay = document.createElement('div');
        overlay.id = 'book-animation-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0)';
        overlay.style.zIndex = '9997';
        overlay.style.cursor = 'wait';
        document.body.appendChild(overlay);

        // Create book icon
        const book = createBookIcon();

        // Create particles (sparkles)
        const particles = [];
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;

        for (let i = 0; i < particleCount; i++) {
            const angle = (i / particleCount) * Math.PI * 2;
            const radius = 80;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            particles.push(createParticle(x, y));
        }

        try {
            // Choose animation method
            let animationPromise;
            if (hasGSAP) {
                animateWithGSAP(book, particles);
                animationPromise = new Promise((resolve) => {
                    setTimeout(resolve, duration * 1000 + 500);
                });
            } else {
                animationPromise = animateWithCSS(book, particles);
            }

            // Wait for animation to complete
            await animationPromise;

            // Cleanup
            book.remove();
            particles.forEach((p) => p.remove());
            overlay.remove();

            // Trigger callback if provided
            if (typeof options.onComplete === 'function') {
                options.onComplete();
            }

            return true;
        } catch (error) {
            console.error('Book animation error:', error);
            book.remove();
            particles.forEach((p) => p.remove());
            overlay.remove();
            return false;
        }
    };

    /**
     * Alternative: Page turn animation variant
     */
    window.animatePageTurn = async function(options) {
        options = options || {};

        // Add page turn styles if not already present
        if (!document.getElementById('page-turn-styles')) {
            const style = document.createElement('style');
            style.id = 'page-turn-styles';
            style.innerHTML = `
                @keyframes pageTurn {
                    0% { transform: rotateX(0deg) rotateZ(0deg); opacity: 1; }
                    50% { transform: rotateX(45deg) rotateZ(-5deg); }
                    100% { transform: rotateX(0deg) rotateZ(0deg); opacity: 0; }
                }

                .page-turning {
                    animation: pageTurn 1.5s ease-in-out forwards;
                }
            `;
            document.head.appendChild(style);
        }

        const page = document.createElement('div');
        page.className = 'page-turning';
        page.style.position = 'fixed';
        page.style.top = '0';
        page.style.left = '0';
        page.style.width = '100%';
        page.style.height = '100%';
        page.style.backgroundColor = 'var(--vtt-bg)';
        page.style.zIndex = '9999';
        page.style.perspective = '1000px';
        document.body.appendChild(page);

        return new Promise((resolve) => {
            setTimeout(() => {
                page.remove();
                if (typeof options.onComplete === 'function') {
                    options.onComplete();
                }
                resolve();
            }, 1500);
        });
    };

    /**
     * Combined effect: Book open + page turn
     */
    window.animateFullSpellbookOpening = async function(options) {
        options = options || {};

        // Animate book opening
        await animateBookOpen({
            duration: options.bookDuration || 2.5,
            particleCount: options.particleCount || 12,
            onComplete: options.afterBook || null
        });

        // Then animate page turn
        if (options.includePageTurn !== false) {
            await animatePageTurn({
                onComplete: options.onComplete || null
            });
        }
    };

    /**
     * Initialize animations when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAnimations);
    } else {
        initializeAnimations();
    }

    function initializeAnimations() {
        // Add stylesheet link if needed
        const linkCSS = document.createElement('link');
        linkCSS.rel = 'stylesheet';
        linkCSS.href = '/static/css/spellbook-theme.css';
        if (!document.querySelector('link[href="/static/css/spellbook-theme.css"]')) {
            document.head.appendChild(linkCSS);
        }
    }

})();
