/** @type {import('tailwindcss').Config} */
// Andd Baay — config Tailwind v3 pour build prod (remplace le CDN runtime).
// Mirror exact de l'ancienne config CDN dans templates/includes/tailwind_htmx_alpine_head.html :
//   - prefix tw- pour éviter les collisions avec Bootstrap.
//   - preflight désactivé pour ne pas casser les resets Bootstrap.

module.exports = {
    prefix: 'tw-',
    content: [
        './templates/**/*.html',
        './baay/templates/**/*.html',
        './baay/static/js/**/*.js',
        './baay/**/*.py',
    ],
    corePlugins: {
        preflight: false,
    },
    darkMode: ['class', '[data-bs-theme="dark"]'],
    theme: {
        extend: {
            colors: {
                'brand-primary': '#1D9E75',
                'brand-deep': '#085041',
                'brand-night': '#04342C',
                'brand-pale': '#9FE1CB',
                'brand-light': '#5DCAA5',
                'brand-bg': '#E1F5EE',
                'brand-accent': '#EF9F27',
            },
        },
    },
    plugins: [],
};
