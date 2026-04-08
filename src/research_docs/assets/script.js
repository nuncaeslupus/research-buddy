/* ─────────────────────────────────────────────────────────────────────────
   AI Trading System — Master Reference  |  build.py generated
   All behaviour inside DOMContentLoaded. No inline onclick attributes.
───────────────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', function() {

const TABS = /*TABS_INJECT*/['overview','research','theory','design','implementation','changelog']/*END_INJECT*/;

/* ── helpers ── */
function $(id) { return document.getElementById(id); }

/* ── Tab switching ────────────────────────────────────────────────────── */
function switchTab(tab, noSave) {
  TABS.forEach(function(t) {
    var content = $('tab-' + t);
    if (content) content.classList.toggle('active', t === tab);
    var btn = document.querySelector('.tab-btn[data-tab="' + t + '"]');
    if (btn) btn.classList.toggle('active', t === tab);
    var nav = document.querySelector('.tab-nav[data-for="' + t + '"]');
    if (nav) nav.classList.toggle('active', t === tab);
  });
  var sb = $('sidebar');
  if (window.innerWidth <= 768 && sb) sb.classList.remove('open');
  if (!noSave) try { sessionStorage.setItem('activeTab', tab); } catch(e) {}
}

/* Tab bar clicks — event delegation on #tab-bar */
var tabBar = $('tab-bar');
if (tabBar) {
  tabBar.addEventListener('click', function(e) {
    var btn = e.target.closest('.tab-btn[data-tab]');
    if (btn) {
      switchTab(btn.getAttribute('data-tab'));
      $('main').scrollTo(0, 0);
    }
  });
}

/* ── Sidebar toggle (mobile) ─────────────────────────────────────────── */
var menuToggle = $('menu-toggle');
if (menuToggle) {
  menuToggle.addEventListener('click', function() {
    var sb = $('sidebar');
    if (sb) sb.classList.toggle('open');
  });
}

/* ── Cross-tab xlinks ────────────────────────────────────────────────── */
document.addEventListener('click', function(e) {
  var link = e.target.closest('a.xlink[data-tab]');
  if (!link) return;
  e.preventDefault();
  var tab  = link.getAttribute('data-tab');
  var href = link.getAttribute('href');
  
  switchTab(tab, true);
  
  if (href && href.startsWith('#')) {
    var targetId = href.slice(1);
    var attempts = 0;
    var interval = setInterval(function() {
      var el = document.getElementById(targetId);
      if (el && el.offsetParent !== null) {
        clearInterval(interval);
        var main = $('main');
        var top = el.getBoundingClientRect().top - main.getBoundingClientRect().top + main.scrollTop - 20;
        main.scrollTo({ top: top, behavior: 'smooth' });
      }
      if (++attempts > 10) clearInterval(interval);
    }, 50);
  }
});

/* Restore saved tab on load */
try {
  var saved = sessionStorage.getItem('activeTab');
  if (saved && TABS.indexOf(saved) >= 0) switchTab(saved, true);
} catch(e) {}

/* ── Active nav highlighting on scroll ───────────────────────────────── */
var _mainArea = $('main');

function updateSpy() {
  if (!_mainArea) return;
  
  var activeContent = document.querySelector('.tab-content.active');
  if (!activeContent) return;
  
  // Find all elements with an ID that are headers or section-like containers
  var targets = Array.from(activeContent.querySelectorAll('h1[id], section[id], div[id].level-3, div[id].level-4'));
  var best = null;
  var mainRect = _mainArea.getBoundingClientRect();

  for (var i = 0; i < targets.length; i++) {
    var el = targets[i];
    var rect = el.getBoundingClientRect();
    // Use a threshold of 100px from the top of the viewport area
    if (rect.top - mainRect.top <= 100) {
      best = el;
    } else {
      break;
    }
  }
  
  if (best) {
    var id = best.id;
    var activeNav = document.querySelector('.tab-nav.active');
    if (activeNav) {
      activeNav.querySelectorAll('a').forEach(function(l) {
        var href = l.getAttribute('href');
        l.classList.toggle('active', href === '#' + id);
      });
    }
  }
}

if (_mainArea) {
  _mainArea.addEventListener('scroll', updateSpy, { passive: true });
}

/* ── Copy code buttons — event delegation ────────────────────────────── */
document.addEventListener('click', function(e) {
  var btn = e.target.closest('.copy-btn');
  if (!btn) return;
  var pre = btn.nextElementSibling;
  var text = pre ? pre.textContent : '';
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = '✓';
    btn.classList.add('copied');
    setTimeout(function() { btn.textContent = '⎘'; btn.classList.remove('copied'); }, 1800);
  }).catch(function() {
    btn.textContent = '!';
    setTimeout(function() { btn.textContent = '⎘'; }, 1500);
  });
});

if (typeof hljs !== 'undefined') hljs.highlightAll();

});
