/**
 * Andd Baay — Liste projets (recherche debounced + sticky bar)
 */
(function () {
    'use strict';

    var root = document.querySelector('.pl-page');
    if (!root) return;

    var form = document.getElementById('plSearchForm');
    var input = document.getElementById('plSearchInput');
    var controls = document.getElementById('plControls');
    var debounceTimer;

    if (form && input) {
        input.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                form.submit();
            }, 400);
        });
    }

    if (controls && 'IntersectionObserver' in window) {
        var sentinel = document.createElement('div');
        sentinel.setAttribute('aria-hidden', 'true');
        sentinel.style.cssText = 'height:1px;margin-top:-1px;';
        controls.parentNode.insertBefore(sentinel, controls);
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                controls.classList.toggle('is-stuck', !e.isIntersecting);
            });
        }, { threshold: 0, rootMargin: '-1px 0px 0px 0px' });
        io.observe(sentinel);
    }
})();
