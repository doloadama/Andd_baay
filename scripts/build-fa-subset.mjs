#!/usr/bin/env node
/**
 * Andd Baay — Font Awesome subset builder.
 *
 * Lit `.fa-icons-used.txt` (généré par audit perf, voir perf-audit.md action #3)
 * et produit :
 *   - baay/static/webfonts/fa-{solid,brands}.woff2 (subsets via `fontawesome-subset`)
 *   - baay/static/css/fa-subset.css (CSS minimal avec @font-face + uniquement les
 *     règles `.fa-{name}::before` pour les icônes utilisées).
 *
 * À lancer :  npm run build:fa
 *
 * Pour ajouter une icône : insérer son nom dans `.fa-icons-used.txt` (ou regénérer
 * le fichier en grepant le code) puis relancer `npm run build:css`.
 */

import { fontawesomeSubset } from 'fontawesome-subset';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

const ICONS_FILE = join(ROOT, '.fa-icons-used.txt');
const FA_CSS = join(ROOT, 'node_modules/@fortawesome/fontawesome-free/css/all.css');
const WEBFONTS_DIR = join(ROOT, 'baay/static/webfonts');
const OUT_CSS = join(ROOT, 'baay/static/css/fa-subset.css');

// Liste curated des icônes brands (FA 6 brands.svg). Tout le reste est solid.
// Étendre si une nouvelle icône brand est ajoutée.
const BRAND_ICONS = new Set([
    'twitter', 'x-twitter', 'instagram', 'linkedin-in', 'linkedin',
    'facebook', 'facebook-f', 'github', 'whatsapp', 'youtube',
    'tiktok', 'discord', 'telegram', 'snapchat', 'pinterest',
]);

function readIcons() {
    if (!existsSync(ICONS_FILE)) {
        throw new Error(`Liste d'icônes manquante : ${ICONS_FILE}. Regénérer via le script PowerShell d'audit (voir perf-audit.md).`);
    }
    return readFileSync(ICONS_FILE, 'utf-8')
        .split(/\r?\n/)
        .map(s => s.trim())
        .filter(Boolean);
}

function partition(icons) {
    const solid = [];
    const brands = [];
    for (const name of icons) {
        if (BRAND_ICONS.has(name)) brands.push(name);
        else solid.push(name);
    }
    return { solid, brands };
}

// Modifiers FA (utilitaires) — toujours conservés, jamais traités comme des icônes.
const MODIFIERS = new Set([
    'fw', 'sm', 'lg', 'xs', '2x', '3x', '4x', '5x', '6x', '7x', '8x', '9x', '10x',
    'spin', 'spin-pulse', 'spin-reverse', 'pulse',
    'beat', 'beat-fade', 'bounce', 'fade', 'flash',
    'flip', 'flip-horizontal', 'flip-vertical', 'flip-both', 'shake',
    'rotate-90', 'rotate-180', 'rotate-270', 'rotate-by',
    'stack', 'stack-1x', 'stack-2x', 'inverse',
    'border', 'pull-left', 'pull-right',
    'li', 'ul', 'ulist',
    'layers', 'layers-text', 'layers-counter', 'inline', 'swap-opacity',
]);

/**
 * Détermine si un sélecteur doit être conservé.
 * Conserve : :root, :host, les classes structurelles (.fa, .fas, .far, .fab),
 *            les modifiers (.fa-fw, .fa-spin, …),
 *            les icônes en wanted (.fa-eye, .fa-eye::before, …),
 *            les groupes contenant au moins une icône wanted ou un modifier ou structurel.
 */
function shouldKeepSelector(selector, wanted) {
    const parts = selector.split(',').map(s => s.trim()).filter(Boolean);
    for (const sel of parts) {
        const base = sel.replace(/::?[\w-]+(\([^)]*\))?\s*$/, '').trim();
        if (base === ':root' || base === ':host') return true;
        if (base === '.fa' || base === '.fas' || base === '.far' || base === '.fab' || base === '.fa-classic' || base === '.fa-sharp' || base === '.fa-solid' || base === '.fa-regular' || base === '.fa-brands') return true;
        const iconMatch = base.match(/^\.fa-([a-z][\w-]*)$/);
        if (iconMatch) {
            const name = iconMatch[1];
            if (MODIFIERS.has(name)) return true;
            if (wanted.has(name)) return true;
        }
    }
    return false;
}

/**
 * Filtre `all.css` : garde
 *   - :root et :host (variables --fa-*),
 *   - classes structurelles (.fa, .fas, .far, .fab) et modifiers,
 *   - règles d'icônes (.fa-{name} ou .fa-{name}::before) pour `wanted` uniquement,
 *   - tous les @keyframes (utilisés par les modifiers),
 *   - les @font-face (pointent vers ../webfonts/ — réécrits par fontawesome-subset).
 */
function buildCss(fullCss, wantedIcons) {
    const wanted = new Set(wantedIcons);
    const out = [];

    // 1) @-rules à passes multiples (font-face, keyframes, prefers-reduced-motion)
    const atFontFaceRegex = /@font-face\s*\{[^}]*\}/g;
    const atKeyframesRegex = /@(?:-webkit-)?keyframes\s+[\w-]+\s*\{(?:[^{}]*\{[^{}]*\}[^{}]*)*\}/g;
    const atMediaRegex = /@media[^{]*\{(?:[^{}]*\{[^{}]*\}[^{}]*)*\}/g;
    let m;
    while ((m = atFontFaceRegex.exec(fullCss)) !== null) out.push(m[0]);
    while ((m = atKeyframesRegex.exec(fullCss)) !== null) out.push(m[0]);
    while ((m = atMediaRegex.exec(fullCss)) !== null) out.push(m[0]);

    // 2) Règles plates (sélecteur { body }) — exclut tout ce qui contient `@`.
    const ruleRegex = /([^{}@]+?)\{([^{}]*)\}/g;
    while ((m = ruleRegex.exec(fullCss)) !== null) {
        const selector = m[1].trim();
        const body = m[2];
        if (!selector || !body.trim()) continue;
        if (shouldKeepSelector(selector, wanted)) {
            out.push(`${selector}{${body}}`);
        }
    }

    return [
        '/* Font Awesome subset — généré par scripts/build-fa-subset.mjs.',
        ' * NE PAS ÉDITER : regénérer via `npm run build:fa`.',
        ' * Source : @fortawesome/fontawesome-free (' + wantedIcons.length + ' icônes utilisées).',
        ' */',
        ...out,
    ].join('\n');
}

async function main() {
    const icons = readIcons();
    const { solid, brands } = partition(icons);
    console.log(`Icônes lues   : ${icons.length} (${solid.length} solid, ${brands.length} brands)`);

    if (!existsSync(WEBFONTS_DIR)) mkdirSync(WEBFONTS_DIR, { recursive: true });

    console.log('Génération des WOFF2 subsets…');
    await fontawesomeSubset(
        { solid, brands },
        WEBFONTS_DIR,
        { targetFormats: ['woff2'], package: 'free' },
    );

    console.log('Construction du CSS subset…');
    const fullCss = readFileSync(FA_CSS, 'utf-8');
    const subsetCss = buildCss(fullCss, icons);
    writeFileSync(OUT_CSS, subsetCss, 'utf-8');

    const sizeKb = (subsetCss.length / 1024).toFixed(1);
    console.log(`✔ ${OUT_CSS} (${sizeKb} KB)`);
    console.log(`✔ Fonts dans ${WEBFONTS_DIR}/fa-{solid-900,brands-400}.woff2`);
}

main().catch(e => { console.error(e); process.exit(1); });
