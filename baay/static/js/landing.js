/**
 * Andd Baay — Landing page interactions
 */
(function () {
    'use strict';

    var root = document.querySelector('.lp-page');
    if (!root) return;

    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!reduced && 'IntersectionObserver' in window) {
        root.classList.add('lp-js');
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('is-in');
                    io.unobserve(e.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
        root.querySelectorAll('.lp-rv').forEach(function (el) {
            io.observe(el);
        });
    }

    if (!reduced) {
        root.querySelectorAll('.lp-feat').forEach(function (card) {
            card.addEventListener('pointermove', function (e) {
                var r = card.getBoundingClientRect();
                card.style.setProperty('--lp-mx', (e.clientX - r.left) + 'px');
                card.style.setProperty('--lp-my', (e.clientY - r.top) + 'px');
            });
        });
    }
})();
