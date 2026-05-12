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

  function swapHeadStyles(newDoc) {
    // Remove elements injected by a previous pjax navigation
    document.querySelectorAll('[data-pjax-injected]').forEach(el => el.remove());

    // Inject inline <style> tags from the new page's <head>
    newDoc.querySelectorAll('head style').forEach(s => {
      const clone = document.createElement('style');
      clone.setAttribute('data-pjax-injected', '');
      clone.textContent = s.textContent;
      document.head.appendChild(clone);
    });

    // Inject new <link rel="stylesheet"> not already present in current head
    const existingHrefs = new Set(
      Array.from(document.querySelectorAll('head link[rel="stylesheet"]')).map(l => l.href)
    );
    newDoc.querySelectorAll('head link[rel="stylesheet"]').forEach(l => {
      const href = new URL(l.getAttribute('href'), location.href).href;
      if (!existingHrefs.has(href)) {
        const clone = document.createElement('link');
        clone.rel = 'stylesheet';
        clone.href = href;
        clone.setAttribute('data-pjax-injected', '');
        document.head.appendChild(clone);
      }
    });
  }

  function executeScripts(container) {
    // innerHTML does not run <script> tags — recreate them so they execute
    container.querySelectorAll('script').forEach(oldScript => {
      const newScript = document.createElement('script');
      Array.from(oldScript.attributes).forEach(attr =>
        newScript.setAttribute(attr.name, attr.value)
      );
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode.replaceChild(newScript, oldScript);
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
    // 1. Swap page-specific <head> styles
    swapHeadStyles(newDoc);
    // 2. Replace main content
    curMain.innerHTML = newMain.innerHTML;
    // 3. Re-execute inline scripts inside main (innerHTML suppresses execution)
    executeScripts(curMain);
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
