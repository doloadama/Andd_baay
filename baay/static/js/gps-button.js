/**
 * gps-button.js — Injects a "Locate me" button next to latitude/longitude fields
 * Works on any page containing <input[name*="latitude"]> and <input[name*="longitude"]>
 */
(function () {
  'use strict';

  function initGPSButton() {
    const latInput = document.querySelector('input[name="latitude"], input[name*="latitude"]');
    const lngInput = document.querySelector('input[name="longitude"], input[name*="longitude"]');
    if (!latInput || !lngInput) return;

    // Find the wrapper .mb-4 container of latInput
    let container = latInput.closest('.mb-4');
    if (!container) return;

    // Create button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-gps-locate';
    btn.innerHTML = '<i class="fas fa-location-arrow"></i> Me localiser';
    btn.title = 'Obtenir ma position GPS';

    // Style inline for resilience (also class in mobile.css)
    btn.style.cssText = `
      display:inline-flex;align-items:center;gap:6px;
      margin-top:8px;padding:6px 12px;border-radius:8px;
      border:1px solid var(--border-color);background:var(--card-bg);
      color:var(--text-muted);font-size:0.82rem;font-weight:500;
      cursor:pointer;transition:all .15s ease;
    `;
    btn.addEventListener('mouseenter', () => {
      btn.style.borderColor = 'var(--accent)';
      btn.style.color = 'var(--accent)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.borderColor = 'var(--border-color)';
      btn.style.color = 'var(--text-muted)';
    });

    // Insert after the input-wrapper (or after label)
    const wrapper = container.querySelector('.input-wrapper') || latInput.parentElement;
    if (wrapper && wrapper.nextElementSibling) {
      wrapper.parentElement.insertBefore(btn, wrapper.nextElementSibling);
    } else {
      container.appendChild(btn);
    }

    // Geolocation handler
    btn.addEventListener('click', function () {
      if (!navigator.geolocation) {
        alert('La géolocalisation n\'est pas supportée par ce navigateur.');
        return;
      }
      btn.disabled = true;
      const originalText = btn.innerHTML;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Localisation...';

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          latInput.value = pos.coords.latitude.toFixed(6);
          lngInput.value = pos.coords.longitude.toFixed(6);
          btn.innerHTML = '<i class="fas fa-check"></i> Position trouvée';
          setTimeout(() => { btn.innerHTML = originalText; btn.disabled = false; }, 1500);
        },
        (err) => {
          console.warn('[GPS]', err);
          btn.innerHTML = '<i class="fas fa-exclamation-circle"></i> Erreur GPS';
          setTimeout(() => { btn.innerHTML = originalText; btn.disabled = false; }, 2000);
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
      );
    });
  }

  document.addEventListener('DOMContentLoaded', initGPSButton);
  document.addEventListener('pjax:complete', initGPSButton);
})();
