// script.js — Study Wawa shared JS
// Auth, header scroll, and smooth scroll are handled inline in each page.
// This file is kept for backwards compatibility.

document.addEventListener('DOMContentLoaded', function () {
    // Header scroll effect (fallback for pages that don't inline it)
    const header = document.querySelector('.header');
    if (header && !header.id) {
        window.addEventListener('scroll', function () {
            header.classList.toggle('scrolled', window.scrollY > 60);
        }, { passive: true });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Lazy loading images
    const images = document.querySelectorAll('img[data-src]');
    if (images.length) {
        const imageObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });
        images.forEach(function (img) { imageObserver.observe(img); });
    }

    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js').catch(function () {});
    }
});
