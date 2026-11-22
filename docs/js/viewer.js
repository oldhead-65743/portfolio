// Detail page image viewer: big image + arrows + thumbnail strip.
(function () {
  'use strict';

  function init() {
    var viewer = document.querySelector('[data-viewer]');
    if (!viewer) return;

    var stageImg = viewer.querySelector('[data-viewer-img]');
    var caption = viewer.querySelector('[data-viewer-caption]');
    var counter = viewer.querySelector('[data-viewer-counter]');
    var prevBtn = viewer.querySelector('[data-viewer-prev]');
    var nextBtn = viewer.querySelector('[data-viewer-next]');
    var thumbs = Array.prototype.slice.call(viewer.querySelectorAll('[data-thumb]'));
    if (!stageImg || !thumbs.length) return;

    var n = thumbs.length;
    var current = 0;

    function go(i) {
      current = (i + n) % n;
      var t = thumbs[current];
      stageImg.src = t.getAttribute('data-full') || t.querySelector('img').src;
      stageImg.alt = t.getAttribute('data-alt') || '';
      if (caption) caption.textContent = t.getAttribute('data-caption') || '';
      if (counter) counter.textContent = (current + 1) + ' / ' + n;
      thumbs.forEach(function (el, k) {
        el.classList.toggle('is-active', k === current);
      });
    }

    thumbs.forEach(function (thumb, k) {
      thumb.addEventListener('click', function () { go(k); });
    });
    if (prevBtn) prevBtn.addEventListener('click', function () { go(current - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { go(current + 1); });

    go(0);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
