// About page: Japanese / English toggle.
(function () {
  'use strict';

  function init() {
    var toggle = document.querySelector('[data-lang-toggle]');
    if (!toggle) return;
    var buttons = Array.prototype.slice.call(toggle.querySelectorAll('button[data-lang]'));
    var panels = Array.prototype.slice.call(document.querySelectorAll('.about-lang, .exh-lang'));

    function set(lang) {
      panels.forEach(function (p) {
        p.hidden = p.getAttribute('data-lang') !== lang;
      });
      buttons.forEach(function (b) {
        var on = b.getAttribute('data-lang') === lang;
        b.classList.toggle('is-active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }

    buttons.forEach(function (b) {
      b.addEventListener('click', function () {
        set(b.getAttribute('data-lang'));
      });
    });

    set('ja');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
