/**
 * pjax-lite — partial page reload for nav links.
 * Intercepts [data-pjax] clicks, fetches target HTML, swaps <main id="main">
 * and updates history. Falls back to normal navigation on failure.
 */
(function () {
  'use strict';

  const MAIN_SELECTOR = 'main#main';
  const PJAX_ATTR = 'data-pjax';
  const ACTIVE_CLASS = 'active';

  function findMain(doc) {
    return doc.querySelector(MAIN_SELECTOR);
  }

  function updateTitle(doc) {
    const title = doc.querySelector('title');
    if (title) document.title = title.textContent;
  }

  function updateNavState(url) {
    document.querySelectorAll(`[${PJAX_ATTR}]`).forEach(link => {
      const href = link.getAttribute('href');
      // strip query string for comparison
      const cleanHref = href ? href.split('?')[0] : '';
      const cleanUrl = url.split('?')[0];
      const isActive = cleanUrl === cleanHref ||
        (cleanHref !== '/' && cleanUrl.startsWith(cleanHref));
      link.classList.toggle(ACTIVE_CLASS, isActive);
      if (isActive && link.classList.contains('nav-link-modern')) {
        link.setAttribute('aria-current', 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }

  function swapMain(html, url) {
    const parser = new DOMParser();
    const newDoc = parser.parseFromString(html, 'text/html');
    const newMain = findMain(newDoc);
    const curMain = findMain(document);
    if (!newMain || !curMain) {
      console.warn('[pjax] <main id="main"> not found; falling back to full load.');
      window.location.href = url;
      return false;
    }
    // Replace content
    curMain.innerHTML = newMain.innerHTML;
    updateTitle(newDoc);
    updateNavState(url);
    window.scrollTo({ top: 0, behavior: 'instant' });
    // Dispatch synthetic event so other scripts can re-initialize
    document.dispatchEvent(new CustomEvent('pjax:complete', {
      detail: { url: url }
    }));
    return true;
  }

  async function loadUrl(url, pushState = true) {
    try {
      const resp = await fetch(url, {
        headers: { 'X-PJAX': '1', 'Accept': 'text/html' },
        credentials: 'same-origin'
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();
      if (swapMain(html, url) && pushState) {
        history.pushState({ pjax: true, url: url }, '', url);
      }
    } catch (err) {
      console.warn('[pjax] fetch failed, falling back:', err);
      window.location.href = url;
    }
  }

  function onClick(e) {
    const link = e.target.closest(`a[${PJAX_ATTR}]`);
    if (!link) return;

    // Respect modifiers / middle-click / download / external
    if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') ||
        href.startsWith('tel:') || link.hasAttribute('download')) return;
    if (new URL(href, window.location.href).origin !== window.location.origin) return;

    e.preventDefault();
    loadUrl(href, true);
  }

  // Listen on document for bubbled clicks
  document.addEventListener('click', onClick);

  // Handle back/forward
  window.addEventListener('popstate', function (e) {
    if (e.state && e.state.pjax && e.state.url) {
      loadUrl(e.state.url, false);
    }
  });

  // Initial state
  if (!history.state || !history.state.pjax) {
    history.replaceState({ pjax: true, url: location.href }, '', location.href);
  }
})();
