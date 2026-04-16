// Anti-Flash : Applique le thème avant le rendu du body
let savedTheme = null;
try {
    savedTheme = localStorage.getItem('theme');
} catch (e) {
    savedTheme = null;
}

if (savedTheme !== 'light' && savedTheme !== 'dark') {
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    savedTheme = systemPrefersDark ? 'dark' : 'light';
}

if (savedTheme === 'light') {
    document.documentElement.setAttribute('data-bs-theme', 'light');
    document.documentElement.classList.add('light-mode');
    document.documentElement.classList.remove('dark-mode');
} else {
    document.documentElement.setAttribute('data-bs-theme', 'dark');
    document.documentElement.classList.add('dark-mode');
    document.documentElement.classList.remove('light-mode');
}

const themeColorMeta = document.querySelector('meta[name="theme-color"]');
if (themeColorMeta) {
    themeColorMeta.setAttribute('content', savedTheme === 'dark' ? '#0a0d0a' : '#f4f3ef');
}
