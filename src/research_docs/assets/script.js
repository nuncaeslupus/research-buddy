/* ─────────────────────────────────────────────────────────────────────────
   AI Trading System — Master Reference  |  build.py generated
   All behaviour inside DOMContentLoaded. No inline onclick attributes.
───────────────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', function() {

const TABS = /*TABS_INJECT*/['overview','research','theory','design','implementation','changelog']/*END_INJECT*/;
const HEADER_OFFSET_PX = 90;

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
  clearSearch();
  window.scrollTo(0, 0);
}

/* Tab bar clicks — event delegation on #tab-bar */
var tabBar = $('tab-bar');
if (tabBar) {
  tabBar.addEventListener('click', function(e) {
    var btn = e.target.closest('.tab-btn[data-tab]');
    if (btn) switchTab(btn.getAttribute('data-tab'));
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

/* Close sidebar when clicking outside (mobile) */
document.addEventListener('click', function(e) {
  if (window.innerWidth > 768) return;
  var sb = $('sidebar');
  if (!sb) return;
  if (!sb.contains(e.target) && e.target.id !== 'menu-toggle')
    sb.classList.remove('open');
});

/* ── Cross-tab xlinks ────────────────────────────────────────────────── */
document.addEventListener('click', function(e) {
  var link = e.target.closest('a.xlink[data-tab]');
  if (!link) return;
  e.preventDefault();
  var tab  = link.getAttribute('data-tab');
  var href = link.getAttribute('href');
  switchTab(tab, true);
  if (href && href.startsWith('#')) {
    setTimeout(function() {
      var el = document.getElementById(href.slice(1));
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }
});

/* Restore saved tab on load */
try {
  var saved = sessionStorage.getItem('activeTab');
  if (saved && TABS.indexOf(saved) >= 0) switchTab(saved, true);
} catch(e) {}

/* ── Scroll spy + breadcrumb ─────────────────────────────────────────── */
var _breadcrumb = $('breadcrumb');
var _backTop    = $('back-top');
var _allHeaders = Array.from(
  document.querySelectorAll('h2[id], h3[id], section[id], div[id^="ov-"]')
);

function updateSpy() {
  var scrollY = window.scrollY;
  var best = null;
  for (var i = _allHeaders.length - 1; i >= 0; i--) {
    var el = _allHeaders[i];
    if (!el.closest('.tab-content.active')) continue;
    if (el.getBoundingClientRect().top <= HEADER_OFFSET_PX) { best = el; break; }
  }
  if (best) {
    var id = best.id;
    document.querySelectorAll('#sidebar a').forEach(function(l) {
      l.classList.toggle('active', l.getAttribute('href') === '#' + id);
    });
    var txt = best.textContent.trim().replace(/[★↗]/g, '').trim();
    if (_breadcrumb) {
      if (txt && scrollY > 120) {
        _breadcrumb.textContent = txt;
        _breadcrumb.classList.add('visible');
      } else {
        _breadcrumb.classList.remove('visible');
      }
    }
  }
  if (_backTop) _backTop.classList.toggle('visible', scrollY > 400);
}
window.addEventListener('scroll', updateSpy, { passive: true });

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

/* ── Back to top ─────────────────────────────────────────────────────── */
if (_backTop) {
  _backTop.addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ── In-page search ──────────────────────────────────────────────────── */
var _searchInput = $('search-input');
var _searchCount = $('search-count');
var _marks   = [];
var _markIdx = -1;

function clearSearch() {
  _marks.forEach(function(m) {
    var p = m.parentNode;
    if (p) p.replaceChild(document.createTextNode(m.textContent), m);
  });
  _marks = [];
  _markIdx = -1;
  if (_searchCount) _searchCount.textContent = '';
  document.body.normalize();
}

function doSearch(query) {
  clearSearch();
  if (!query || query.length < 2) return;
  var q = query.toLowerCase();
  var activeTab = document.querySelector('.tab-content.active');
  if (!activeTab) return;

  var nodes = [];
  var stack = [activeTab];
  while (stack.length) {
    var node = stack.pop();
    if (node.nodeType === 3) {
      if (node.textContent.toLowerCase().indexOf(q) >= 0) nodes.push(node);
    } else if (node.nodeType === 1) {
      var tag = node.tagName;
      if (tag !== 'SCRIPT' && tag !== 'STYLE' && tag !== 'BUTTON') {
        for (var ci = node.childNodes.length - 1; ci >= 0; ci--)
          stack.push(node.childNodes[ci]);
      }
    }
  }

  nodes.forEach(function(textNode) {
    var text = textNode.textContent;
    var lo   = text.toLowerCase();
    var frags = [];
    var last = 0, idx;
    while ((idx = lo.indexOf(q, last)) >= 0) {
      if (idx > last) frags.push(document.createTextNode(text.slice(last, idx)));
      var mark = document.createElement('mark');
      mark.textContent = text.slice(idx, idx + q.length);
      frags.push(mark);
      _marks.push(mark);
      last = idx + q.length;
    }
    if (!frags.length) return;
    if (last < text.length) frags.push(document.createTextNode(text.slice(last)));
    var par = textNode.parentNode;
    frags.forEach(function(f) { par.insertBefore(f, textNode); });
    par.removeChild(textNode);
  });

  if (_marks.length) {
    _markIdx = 0;
    _marks[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (_searchCount) _searchCount.textContent = '1 / ' + _marks.length;
  } else {
    if (_searchCount) _searchCount.textContent = '0 results';
  }
}

function searchNext() {
  if (!_marks.length) return;
  _markIdx = (_markIdx + 1) % _marks.length;
  _marks[_markIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
  if (_searchCount) _searchCount.textContent = (_markIdx + 1) + ' / ' + _marks.length;
}
function searchPrev() {
  if (!_marks.length) return;
  _markIdx = (_markIdx - 1 + _marks.length) % _marks.length;
  _marks[_markIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
  if (_searchCount) _searchCount.textContent = (_markIdx + 1) + ' / ' + _marks.length;
}

if (_searchInput) {
  var _searchTimer = null;
  _searchInput.addEventListener('input', function() {
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(function() { doSearch(_searchInput.value.trim()); }, 250);
  });
  _searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter')  { e.shiftKey ? searchPrev() : searchNext(); }
    if (e.key === 'Escape') { _searchInput.value = ''; clearSearch(); _searchInput.blur(); }
  });
}

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'f' && _searchInput) {
    e.preventDefault();
    _searchInput.focus();
    _searchInput.select();
  }
});

/* ── Syntax highlighting ─────────────────────────────────────────────── */
if (typeof hljs !== 'undefined') hljs.highlightAll();

}); /* end DOMContentLoaded */
