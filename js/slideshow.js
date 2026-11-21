// Top page slideshow: fade between 7 works every N seconds (default 6).
(function () {
  'use strict';

  function init() {
    var show = document.querySelector('[data-slideshow]');
    if (!show) return;

    var slides = Array.prototype.slice.call(show.querySelectorAll('.slideshow__img'));
    var dots = Array.prototype.slice.call(document.querySelectorAll('[data-dot]'));
    var caption = document.querySelector('[data-slide-caption]');
    var link = document.querySelector('[data-slide-link]');
    if (!slides.length) return;

    var seconds = parseInt(show.getAttribute('data-seconds'), 10) || 6;
    var current = 0;
    var timer = null;

    function renderCaption(i) {
      if (!caption) return;
      var img = slides[i];
      caption.innerHTML = '';
      var title = document.createElement('span');
      title.className = 'slide-caption__title';
      title.textContent = img.getAttribute('data-title') || '';
      caption.appendChild(title);
      caption.appendChild(
        document.createTextNode(
          '　' + (img.getAttribute('data-year') || '') +
          '　' + (img.getAttribute('data-place') || '')
        )
      );
    }

    function go(i) {
      current = (i + slides.length) % slides.length;
      slides.forEach(function (el, k) {
        el.classList.toggle('is-active', k === current);
      });
      dots.forEach(function (el, k) {
        el.classList.toggle('is-active', k === current);
      });
      if (link) {
        var href = slides[current].getAttribute('data-href');
        if (href) link.setAttribute('href', href);
        link.setAttribute(
          'aria-label',
          (slides[current].getAttribute('data-title') || '') + 'の作品ページを開く'
        );
      }
      renderCaption(current);
    }

    function start() {
      clearInterval(timer);
      timer = setInterval(function () {
        go(current + 1);
      }, Math.max(2, seconds) * 1000);
    }

    dots.forEach(function (dot, k) {
      dot.addEventListener('click', function () {
        go(k);
        start();
      });
    });

    go(0);
    start();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
