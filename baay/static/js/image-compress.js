/**
 * image-compress.js — Client-side image compression before upload.
 * Targets <input type="file" accept="image/*"> on all pages.
 * Replaces selected files with compressed JPEG versions (max 1600px, quality 0.82).
 */
(function () {
  'use strict';

  const MAX_WIDTH = 1600;
  const QUALITY = 0.82;
  const MAX_FILE_MB = 5; // Skip compression if already small

  function compressImage(file) {
    return new Promise((resolve, reject) => {
      if (!file.type.startsWith('image/') || file.size < 200 * 1024) {
        resolve(file); // already small or not an image
        return;
      }
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = function () {
        URL.revokeObjectURL(url);
        let { width, height } = img;
        if (width > MAX_WIDTH) {
          height = Math.round(height * (MAX_WIDTH / width));
          width = MAX_WIDTH;
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (!blob) { reject(new Error('Canvas toBlob failed')); return; }
            const compressed = new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), {
              type: 'image/jpeg',
              lastModified: Date.now(),
            });
            resolve(compressed);
          },
          'image/jpeg',
          QUALITY
        );
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Image decode failed'));
      };
      img.src = url;
    });
  }

  function showFeedback(input, original, compressed) {
    let label = input.closest('.mb-4, .form-group, .input-wrapper')?.querySelector('label');
    if (!label) return;
    let badge = label.querySelector('.compress-badge');
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'compress-badge';
      badge.style.cssText = 'margin-left:6px;font-size:0.72rem;color:var(--accent);font-weight:600;';
      label.appendChild(badge);
    }
    const beforeMB = (original.size / 1024 / 1024).toFixed(2);
    const afterMB = (compressed.size / 1024 / 1024).toFixed(2);
    badge.textContent = `Compressé : ${beforeMB} Mo → ${afterMB} Mo`;
    setTimeout(() => { if (badge) badge.remove(); }, 4000);
  }

  function bindCompression() {
    document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
      if (input.dataset.compressBound) return;
      input.dataset.compressBound = '1';
      input.addEventListener('change', async function () {
        if (!input.files || !input.files.length) return;
        const file = input.files[0];
        if (file.size > MAX_FILE_MB * 1024 * 1024) {
          // too large even before compression, warn
          console.warn('[ImageCompress] File very large:', file.size);
        }
        try {
          const compressed = await compressImage(file);
          const dt = new DataTransfer();
          dt.items.add(compressed);
          input.files = dt.files;
          showFeedback(input, file, compressed);
        } catch (err) {
          console.warn('[ImageCompress] Compression failed, keeping original:', err);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', bindCompression);
  document.addEventListener('pjax:complete', bindCompression);
})();
