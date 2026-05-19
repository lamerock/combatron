from __future__ import annotations

import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlparse
from zipfile import ZIP_DEFLATED, ZipFile

from .models import Chapter
from .scraper import discover_chapters, fetch_chapter_pages, to_json_ready


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


def _index_html() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Combatron Reader</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0c1117;
      --panel: #131a23;
      --panel-2: #1a2430;
      --panel-3: #212f3f;
      --text: #edf2f7;
      --muted: #95a3b7;
      --accent: #f7ae47;
      --accent-2: #ffd08a;
      --line: #2a3a4d;
      --ok: #7dd3a6;
      --warn: #ffcc70;
      --shadow: 0 20px 48px rgba(3, 6, 10, 0.48);
      --radius: 14px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Bahnschrift", "Trebuchet MS", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 8% -20%, #2a4261 0%, transparent 42%),
        radial-gradient(circle at 105% 0%, #523523 0%, transparent 38%),
        linear-gradient(180deg, #111a25 0%, #0b1119 55%, #090d13 100%);
      color: var(--text);
      min-height: 100vh;
      min-height: 100dvh;
      height: 100dvh;
      overflow: hidden;
    }

    .app {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      min-height: 100vh;
      min-height: 100dvh;
      height: 100dvh;
      overflow: hidden;
    }

    .sidebar {
      border-right: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(13, 19, 28, 0.98), rgba(10, 15, 22, 0.96));
      padding: 16px;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto auto auto minmax(0, 1fr) auto;
      position: relative;
      z-index: 5;
      min-height: 0;
    }

    .brand-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 4px;
    }

    .brand {
      font-size: 1.36rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      margin: 0;
    }

    .badge {
      border: 1px solid rgba(247, 174, 71, 0.32);
      color: var(--accent-2);
      background: rgba(247, 174, 71, 0.08);
      border-radius: 999px;
      font-size: 0.76rem;
      font-weight: 700;
      padding: 4px 10px;
      white-space: nowrap;
    }

    .subtle {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
      margin-bottom: 12px;
    }

    .search-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      margin-bottom: 10px;
    }

    .search {
      width: 100%;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      outline: none;
    }

    .search:focus {
      border-color: rgba(247, 174, 71, 0.6);
      box-shadow: 0 0 0 3px rgba(247, 174, 71, 0.15);
    }

    .ghost-btn {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      border-radius: 12px;
      cursor: pointer;
      padding: 8px 12px;
      font-size: 0.82rem;
    }

    .ghost-btn:hover {
      border-color: #4f6279;
      background: #1c2634;
    }

    .chapter-list {
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
      align-content: start;
      min-height: 0;
      overflow: auto;
      padding-right: 4px;
    }

    .chapter {
      padding: 11px 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: linear-gradient(180deg, #182330, #121c28);
      cursor: pointer;
      transition: transform 0.14s ease, border-color 0.14s ease, background 0.14s ease;
    }

    .chapter:hover {
      transform: translateY(-1px);
      border-color: #4f6480;
      background: linear-gradient(180deg, #1a2736, #152232);
    }

    .chapter.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px rgba(247, 174, 71, 0.2) inset;
    }

    .chapter-title {
      font-weight: 600;
      line-height: 1.32;
    }

    .chapter-url {
      font-size: 0.8rem;
      color: var(--muted);
      margin-top: 4px;
      word-break: break-word;
    }

    .empty {
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      color: var(--muted);
      padding: 14px;
      font-size: 0.9rem;
      text-align: center;
      background: rgba(14, 20, 29, 0.65);
    }

    .tips {
      border-top: 1px solid var(--line);
      padding-top: 12px;
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.55;
    }

    .main {
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      min-width: 0;
      min-height: 0;
      height: 100dvh;
      overflow: hidden;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(11, 17, 26, 0.86);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 3;
    }

    .toolbar button {
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      padding: 9px 13px;
      border-radius: 999px;
      cursor: pointer;
      font-weight: 600;
      letter-spacing: 0.01em;
    }

    .toolbar button:hover {
      border-color: #5e7390;
      background: var(--panel-3);
    }

    .toolbar button:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    .toolbar .primary {
      border-color: rgba(247, 174, 71, 0.5);
      background: linear-gradient(180deg, #5c4221, #4e3618);
      color: #ffe5c0;
    }

    .toolbar .primary:hover {
      border-color: rgba(247, 174, 71, 0.9);
      background: linear-gradient(180deg, #664928, #553b1a);
    }

    .status {
      margin-left: auto;
      color: var(--muted);
      font-size: 0.9rem;
      min-width: 160px;
      text-align: right;
    }

    .meta-status {
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .meta-status #pageInfo {
      white-space: nowrap;
    }

    .meta-status .status {
      margin-left: 0;
    }

    .progress {
      height: 5px;
      width: 100%;
      background: #0d141d;
      border-bottom: 1px solid var(--line);
    }

    .progress > span {
      display: block;
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #f6ad55, #fbd38d);
      transition: width 0.2s ease;
    }

    .viewer {
      overflow: auto;
      padding: 18px 14px 24px;
      display: grid;
      justify-items: center;
      align-content: start;
      gap: 16px;
      min-width: 0;
      min-height: 0;
      overscroll-behavior: contain;
    }

    .sidebar-scrim {
      display: none;
    }

    .chapter-name {
      width: min(100%, 1040px);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
      color: var(--muted);
      padding: 2px 4px;
    }

    .chapter-name strong {
      color: var(--text);
      font-size: 1.08rem;
    }

    .pages {
      width: min(100%, 1040px);
      display: grid;
      gap: 18px;
    }

    .page {
      background: #000;
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: var(--shadow);
      transition: transform 0.15s ease, border-color 0.15s ease;
    }

    .page.active {
      border-color: rgba(247, 174, 71, 0.7);
      transform: translateY(-1px);
    }

    .page img {
      display: block;
      width: 100%;
      height: auto;
      transform-origin: top center;
      transition: transform 0.15s ease;
    }

    .toast {
      position: fixed;
      right: 14px;
      bottom: 14px;
      border: 1px solid rgba(255, 112, 112, 0.45);
      background: rgba(58, 22, 22, 0.93);
      color: #ffd5d5;
      padding: 11px 14px;
      border-radius: 12px;
      max-width: min(90vw, 420px);
      box-shadow: var(--shadow);
      opacity: 0;
      transform: translateY(6px);
      pointer-events: none;
      transition: opacity 0.16s ease, transform 0.16s ease;
      z-index: 20;
      font-size: 0.9rem;
    }

    .toast.show {
      opacity: 1;
      transform: translateY(0);
    }

    .disclaimer-modal {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      z-index: 31;
    }

    .disclaimer-modal.open {
      display: flex;
    }

    .disclaimer-backdrop {
      position: absolute;
      inset: 0;
      border: 0;
      margin: 0;
      padding: 0;
      background: rgba(3, 7, 12, 0.7);
    }

    .disclaimer-card {
      position: relative;
      width: min(92vw, 520px);
      border: 1px solid rgba(247, 174, 71, 0.45);
      border-radius: 16px;
      background: linear-gradient(180deg, #1a2431 0%, #111925 100%);
      box-shadow: var(--shadow);
      padding: 18px;
      z-index: 1;
    }

    .disclaimer-title {
      margin: 0 0 10px;
      font-size: 1.12rem;
    }

    .disclaimer-copy {
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.55;
    }

    .disclaimer-actions {
      display: flex;
      justify-content: flex-end;
    }

    .disclaimer-actions button {
      border: 1px solid rgba(247, 174, 71, 0.7);
      background: linear-gradient(180deg, #654b26, #523a1b);
      color: #ffe8c6;
      padding: 10px 13px;
      border-radius: 999px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
    }

    .donation-modal {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      z-index: 30;
    }

    .donation-modal.open {
      display: flex;
    }

    .donation-backdrop {
      position: absolute;
      inset: 0;
      border: 0;
      margin: 0;
      padding: 0;
      background: rgba(3, 7, 12, 0.66);
      cursor: pointer;
    }

    .donation-card {
      position: relative;
      width: min(92vw, 480px);
      border: 1px solid rgba(247, 174, 71, 0.5);
      border-radius: 16px;
      background: linear-gradient(180deg, #1a2431 0%, #111925 100%);
      box-shadow: var(--shadow);
      padding: 18px;
      z-index: 1;
    }

    .donation-kicker {
      color: var(--accent-2);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      font-weight: 700;
    }

    .donation-title {
      margin: 0 0 8px;
      font-size: 1.14rem;
    }

    .donation-copy {
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.55;
    }

    .donation-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .donation-actions button,
    .donation-actions a {
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      text-decoration: none;
      padding: 10px 13px;
      border-radius: 999px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
    }

    .donation-actions .donate {
      border-color: rgba(247, 174, 71, 0.7);
      background: linear-gradient(180deg, #654b26, #523a1b);
      color: #ffe8c6;
    }

    .donation-actions .continue {
      border-color: #5e7390;
      background: var(--panel-3);
    }

    .drawer-toggle {
      display: none;
    }

    @media (max-width: 980px) {
      .app {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: fixed;
        inset: 0 auto 0 0;
        width: min(92vw, 380px);
        transform: translateX(-102%);
        transition: transform 0.2s ease;
        box-shadow: var(--shadow);
      }

      .app.sidebar-open .sidebar {
        transform: translateX(0);
      }

      .sidebar-scrim {
        display: block;
        position: fixed;
        inset: 0;
        border: 0;
        margin: 0;
        padding: 0;
        background: rgba(2, 6, 10, 0.55);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.18s ease;
        z-index: 4;
      }

      .app.sidebar-open .sidebar-scrim {
        opacity: 1;
        pointer-events: auto;
      }

      .drawer-toggle {
        display: inline-flex;
      }

      .status {
        width: 100%;
        margin-left: 0;
        text-align: left;
      }

      .meta-status {
        width: 100%;
        margin-left: 0;
        justify-content: space-between;
      }

      .meta-status .status {
        min-width: 0;
      }
    }
  </style>
</head>
<body>
  <div id=\"app\" class=\"app\">
    <aside class=\"sidebar\">
      <div class=\"brand-row\">
        <h1 class=\"brand\">Combatron Reader</h1>
        <span id=\"chapterCount\" class=\"badge\">0 chapters</span>
      </div>
      <div class=\"subtle\">Browse chapter labels from Project Combatron and read pages in sequence with fast keyboard controls.</div>
      <div class=\"search-row\">
        <input id=\"search\" class=\"search\" placeholder=\"Search chapters...\" />
        <button id=\"clearSearch\" class=\"ghost-btn\" type=\"button\">Clear</button>
      </div>
      <div id=\"chapters\" class=\"chapter-list\"></div>
      <div class=\"tips\">
        <div><strong>Keyboard:</strong> N/P chapter, J/K page, +/- zoom, F fit width</div>
        <div><strong>Tip:</strong> press / to focus chapter search.</div>
      </div>
    </aside>
    <button id=\"sidebarScrim\" class=\"sidebar-scrim\" type=\"button\" aria-label=\"Close chapter drawer\"></button>
    <main class=\"main\">
      <div class=\"toolbar\">
        <button id=\"toggleSidebar\" class=\"drawer-toggle\" type=\"button\">Chapters</button>
        <button id=\"prevChapter\">Prev Chapter</button>
        <button id=\"nextChapter\">Next Chapter</button>
        <button id=\"prevPage\">Prev Page</button>
        <button id=\"nextPage\">Next Page</button>
        <button id=\"fitWidth\">Fit Width</button>
        <button id=\"zoomOut\">-</button>
        <button id=\"zoomIn\">+</button>
        <button id=\"download\" class=\"primary\" disabled>Export Disabled</button>
        <div class="meta-status">
          <span id="pageInfo">Page 0 of 0</span>
          <span id="status" class="status">Loading chapters...</span>
        </div>
      </div>
      <div class=\"progress\"><span id=\"progressBar\"></span></div>
      <div class=\"viewer\">
        <div class=\"chapter-name\">
          <strong id=\"currentTitle\">No chapter selected</strong>
        </div>
        <div id=\"pages\" class=\"pages\"></div>
      </div>
    </main>
  </div>
  <div id=\"toast\" class=\"toast\"></div>
  <div id=\"disclaimerModal\" class=\"disclaimer-modal\" aria-hidden=\"true\">
    <button id=\"disclaimerBackdrop\" class=\"disclaimer-backdrop\" type=\"button\" aria-label=\"Close disclaimer\"></button>
    <section class=\"disclaimer-card\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"disclaimerTitle\">
      <h2 id=\"disclaimerTitle\" class=\"disclaimer-title\">Disclaimer</h2>
      <p class=\"disclaimer-copy\">This reader is an unofficial fan tool and does not claim ownership of Project Combatron content. The comic is written by Berlin Manalaysay. Please support the original creators and use this for personal reading only.</p>
      <div class=\"disclaimer-actions\">
        <button id=\"acceptDisclaimer\" type=\"button\">I Understand</button>
      </div>
    </section>
  </div>
  <div id=\"donationModal\" class=\"donation-modal\" aria-hidden=\"true\">
    <button id=\"donationBackdrop\" class=\"donation-backdrop\" type=\"button\" aria-label=\"Close donation dialog\"></button>
    <section class=\"donation-card\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"donationTitle\">
      <div class=\"donation-kicker\">Premium Feature</div>
      <h2 id=\"donationTitle\" class=\"donation-title\">Export Current Chapter</h2>
      <p class=\"donation-copy\">Export is part of the premium experience. If this project helps you, please support it with a donation.</p>
      <div class=\"donation-actions\">
        <a class=\"donate\" href=\"https://paypal.me/lamerock\" target=\"_blank\" rel=\"noopener noreferrer\">Donate via PayPal</a>
        <button id=\"continueExport\" class=\"continue\" type=\"button\">I donated, continue export</button>
      </div>
    </section>
  </div>
  <script>
    const state = {
      chapters: [],
      filtered: [],
      currentIndex: -1,
      currentPages: [],
      currentPage: 0,
      currentChapterUrl: '',
      scale: Number(localStorage.getItem('combatron-scale') || 1),
      observer: null,
      scrollTicking: false,
    };

    const els = {
      app: document.getElementById('app'),
      chapters: document.getElementById('chapters'),
      chapterCount: document.getElementById('chapterCount'),
      search: document.getElementById('search'),
      clearSearch: document.getElementById('clearSearch'),
      currentTitle: document.getElementById('currentTitle'),
      pageInfo: document.getElementById('pageInfo'),
      pages: document.getElementById('pages'),
      viewer: document.querySelector('.viewer'),
      status: document.getElementById('status'),
      progressBar: document.getElementById('progressBar'),
      toast: document.getElementById('toast'),
      disclaimerModal: document.getElementById('disclaimerModal'),
      disclaimerBackdrop: document.getElementById('disclaimerBackdrop'),
      acceptDisclaimer: document.getElementById('acceptDisclaimer'),
      donationModal: document.getElementById('donationModal'),
      donationBackdrop: document.getElementById('donationBackdrop'),
      continueExport: document.getElementById('continueExport'),
      sidebarScrim: document.getElementById('sidebarScrim'),
      toggleSidebar: document.getElementById('toggleSidebar'),
      prevChapter: document.getElementById('prevChapter'),
      nextChapter: document.getElementById('nextChapter'),
      prevPage: document.getElementById('prevPage'),
      nextPage: document.getElementById('nextPage'),
      fitWidth: document.getElementById('fitWidth'),
      zoomOut: document.getElementById('zoomOut'),
      zoomIn: document.getElementById('zoomIn'),
      download: document.getElementById('download'),
    };

    const setStatus = (text) => els.status.textContent = text;

    function closeDisclaimerModal() {
      els.disclaimerModal.classList.remove('open');
      els.disclaimerModal.setAttribute('aria-hidden', 'true');
    }

    function showDisclaimerOnFirstLoad() {
      const key = 'combatron-disclaimer-accepted-v1';
      if (localStorage.getItem(key) === 'yes') return;
      els.disclaimerModal.classList.add('open');
      els.disclaimerModal.setAttribute('aria-hidden', 'false');
    }

    function acceptDisclaimer() {
      localStorage.setItem('combatron-disclaimer-accepted-v1', 'yes');
      closeDisclaimerModal();
    }

    function closeDonationModal() {
      els.donationModal.classList.remove('open');
      els.donationModal.setAttribute('aria-hidden', 'true');
    }

    function openDonationModal() {
      els.donationModal.classList.add('open');
      els.donationModal.setAttribute('aria-hidden', 'false');
    }

    function requestPremiumExport() {
      showError(new Error('Export is disabled.'));
    }

    function continueExport() {
      closeDonationModal();
      showError(new Error('Export is disabled.'));
    }

    function showError(error) {
      const message = (error && error.message) ? error.message : String(error || 'Unknown error');
      els.toast.textContent = message;
      els.toast.classList.add('show');
      setTimeout(() => els.toast.classList.remove('show'), 3200);
    }

    function setProgress() {
      if (!state.currentPages.length) {
        els.progressBar.style.width = '0%';
        return;
      }
      const pct = ((state.currentPage + 1) / state.currentPages.length) * 100;
      els.progressBar.style.width = pct.toFixed(2) + '%';
    }

    function setSidebarOpen(open) {
      els.app.classList.toggle('sidebar-open', !!open);
    }

    function syncCurrentPageFromScroll(force = false) {
      if (!state.currentPages.length) return;
      const nodes = Array.from(els.pages.querySelectorAll('.page'));
      if (!nodes.length) return;

      const viewerRect = els.viewer.getBoundingClientRect();
      const anchorY = viewerRect.top + viewerRect.height * 0.35;
      let bestIndex = state.currentPage;
      let bestDistance = Number.POSITIVE_INFINITY;

      nodes.forEach((node) => {
        const idx = Number(node.dataset.index || 0);
        const rect = node.getBoundingClientRect();
        const isInside = anchorY >= rect.top && anchorY <= rect.bottom;
        const distance = isInside ? 0 : Math.min(Math.abs(anchorY - rect.top), Math.abs(anchorY - rect.bottom));
        if (distance < bestDistance) {
          bestDistance = distance;
          bestIndex = idx;
        }
      });

      if (force || bestIndex !== state.currentPage) {
        state.currentPage = bestIndex;
        highlightCurrentPage();
        updatePageInfo();
        updateToolbar();
      }
    }

    function handleViewerScroll() {
      if (state.scrollTicking) return;
      state.scrollTicking = true;
      requestAnimationFrame(() => {
        state.scrollTicking = false;
        syncCurrentPageFromScroll();
      });
    }

    async function loadChapters() {
      const response = await fetch('/api/chapters');
      if (!response.ok) throw new Error('Unable to load chapter list');
      state.chapters = await response.json();
      state.filtered = state.chapters.slice();
      els.chapterCount.textContent = `${state.chapters.length} chapters`;
      renderChapterList();
      if (state.filtered.length) selectChapter(0);
      setStatus(`${state.chapters.length} chapters loaded`);
    }

    function renderChapterList() {
      els.chapters.innerHTML = '';
      if (!state.filtered.length) {
        els.chapters.innerHTML = '<div class="empty">No chapters match that search.</div>';
        return;
      }
      state.filtered.forEach((chapter, index) => {
        const item = document.createElement('div');
        item.className = 'chapter' + (index === state.currentIndex ? ' active' : '');
        item.innerHTML = `<div class=\"chapter-title\">${chapter.title}</div><div class=\"chapter-url\">${chapter.url}</div>`;
        item.addEventListener('click', () => {
          selectChapter(index);
          if (window.matchMedia('(max-width: 980px)').matches) setSidebarOpen(false);
        });
        els.chapters.appendChild(item);
      });
    }

    async function selectChapter(index) {
      if (index < 0 || index >= state.filtered.length) return;
      state.currentIndex = index;
      const chapter = state.filtered[index];
      setStatus(`Loading ${chapter.title}...`);
      const response = await fetch('/api/chapter?url=' + encodeURIComponent(chapter.url));
      if (!response.ok) throw new Error('Unable to load chapter pages');
      const payload = await response.json();
      state.currentPages = payload.image_urls;
      state.currentChapterUrl = payload.chapter.url;
      state.currentPage = 0;
      state.scale = Number(localStorage.getItem('combatron-scale') || state.scale || 1);
      els.currentTitle.textContent = payload.chapter.title;
      renderChapterList();
      renderPages();
      setStatus(payload.image_urls.length ? `${payload.image_urls.length} page(s)` : 'No images found');
      updateToolbar();
    }

    function renderPages() {
      els.pages.innerHTML = '';

      if (!state.currentPages.length) {
        els.pages.innerHTML = '<div class="empty">No images were found for this chapter.</div>';
        updatePageInfo();
        return;
      }

      state.currentPages.forEach((imageUrl, index) => {
        const page = document.createElement('div');
        page.className = 'page';
        page.dataset.index = String(index);
        const proxiedUrl = '/api/image?url=' + encodeURIComponent(imageUrl) + '&referer=' + encodeURIComponent(state.currentChapterUrl || '');
        page.innerHTML = `<img src=\"${proxiedUrl}\" alt=\"Page ${index + 1}\" style=\"transform: scale(${state.scale});\" loading=\"lazy\" />`;
        els.pages.appendChild(page);
      });
      syncCurrentPageFromScroll(true);
    }

    function highlightCurrentPage() {
      els.pages.querySelectorAll('.page').forEach((pageEl, idx) => {
        pageEl.classList.toggle('active', idx === state.currentPage);
      });
    }

    function updatePageInfo() {
      if (!state.currentPages.length) {
        els.pageInfo.textContent = 'Page 0 of 0';
        setProgress();
        return;
      }
      els.pageInfo.textContent = `Page ${Math.min(state.currentPage + 1, state.currentPages.length)} of ${state.currentPages.length}`;
      setProgress();
    }

    function updateToolbar() {
      els.prevChapter.disabled = state.currentIndex <= 0;
      els.nextChapter.disabled = state.currentIndex >= state.filtered.length - 1;
      els.prevPage.disabled = state.currentPage <= 0;
      els.nextPage.disabled = state.currentPage >= state.currentPages.length - 1;
      els.download.disabled = true;
    }

    function jumpPage(delta) {
      if (!state.currentPages.length) return;
      state.currentPage = Math.max(0, Math.min(state.currentPages.length - 1, state.currentPage + delta));
      const page = els.pages.querySelector(`.page[data-index=\"${state.currentPage}\"]`);
      if (page) page.scrollIntoView({ behavior: 'smooth', block: 'center' });
      highlightCurrentPage();
      updatePageInfo();
      updateToolbar();
    }

    function adjustZoom(delta) {
      state.scale = Math.max(0.4, Math.min(2.5, state.scale + delta));
      localStorage.setItem('combatron-scale', String(state.scale));
      els.pages.querySelectorAll('img').forEach((img) => img.style.transform = `scale(${state.scale})`);
      setStatus(`Zoom ${(state.scale * 100).toFixed(0)}%`);
    }

    els.search.addEventListener('input', () => {
      const q = els.search.value.trim().toLowerCase();
      state.filtered = q ? state.chapters.filter((chapter) => chapter.title.toLowerCase().includes(q)) : state.chapters.slice();
      state.currentIndex = -1;
      renderChapterList();
      if (state.filtered.length) selectChapter(0);
    });

    els.clearSearch.addEventListener('click', () => {
      els.search.value = '';
      state.filtered = state.chapters.slice();
      state.currentIndex = -1;
      renderChapterList();
      if (state.filtered.length) selectChapter(0);
      els.search.focus();
    });

    els.prevChapter.addEventListener('click', () => selectChapter(state.currentIndex - 1));
    els.nextChapter.addEventListener('click', () => selectChapter(state.currentIndex + 1));
    els.prevPage.addEventListener('click', () => jumpPage(-1));
    els.nextPage.addEventListener('click', () => jumpPage(1));
    els.fitWidth.addEventListener('click', () => { state.scale = 1; adjustZoom(0); });
    els.zoomOut.addEventListener('click', () => adjustZoom(-0.1));
    els.zoomIn.addEventListener('click', () => adjustZoom(0.1));
    els.download.addEventListener('click', requestPremiumExport);
    els.continueExport.addEventListener('click', continueExport);
    els.donationBackdrop.addEventListener('click', closeDonationModal);
    els.acceptDisclaimer.addEventListener('click', acceptDisclaimer);
    els.disclaimerBackdrop.addEventListener('click', acceptDisclaimer);

    els.toggleSidebar.addEventListener('click', () => {
      const open = !els.app.classList.contains('sidebar-open');
      setSidebarOpen(open);
    });

    els.sidebarScrim.addEventListener('click', () => setSidebarOpen(false));
    els.viewer.addEventListener('scroll', handleViewerScroll, { passive: true });

    window.addEventListener('keydown', (event) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        if (event.key === 'Escape') {
          event.target.blur();
        }
        return;
      }
      const key = event.key.toLowerCase();
      if (key === '/') {
        event.preventDefault();
        els.search.focus();
      } else if (key === 'n') {
        selectChapter(state.currentIndex + 1).catch(showError);
      } else if (key === 'p') {
        selectChapter(state.currentIndex - 1).catch(showError);
      } else if (key === 'j' || key === 'arrowdown') {
        jumpPage(1);
      } else if (key === 'k' || key === 'arrowup') {
        jumpPage(-1);
      } else if (key === '+' || key === '=') {
        adjustZoom(0.1);
      } else if (key === '-') {
        adjustZoom(-0.1);
      } else if (key === 'f') {
        state.scale = 1;
        adjustZoom(0);
      } else if (key === 'd') {
        showError(new Error('Export is disabled.'));
      } else if (key === 'escape') {
        if (els.disclaimerModal.classList.contains('open')) {
          acceptDisclaimer();
          return;
        }
        closeDonationModal();
        setSidebarOpen(false);
      }
    });

    window.addEventListener('resize', () => {
      if (window.matchMedia('(min-width: 981px)').matches) {
        setSidebarOpen(false);
      }
    });

    showDisclaimerOnFirstLoad();

    loadChapters().catch((error) => {
      setStatus('Failed to load chapters');
      showError(error);
    });
  </script>
</body>
</html>"""


class CombatronHandler(BaseHTTPRequestHandler):
    chapters_cache: list[Chapter] | None = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(_index_html())
            return
        if parsed.path == "/api/chapters":
            self._send_json(to_json_ready(self._chapters()))
            return
        if parsed.path == "/api/chapter":
            query = parse_qs(parsed.query)
            url = query.get("url", [""])[0]
            chapter = self._find_chapter(url)
            if chapter is None:
                self._send_json({"error": "chapter not found"}, status=HTTPStatus.NOT_FOUND)
                return
            chapter_pages = fetch_chapter_pages(chapter)
            self._send_json({
                "chapter": {"title": chapter_pages.chapter.title, "url": chapter_pages.chapter.url},
                "image_urls": list(chapter_pages.image_urls),
            })
            return
        if parsed.path == "/api/image":
            query = parse_qs(parsed.query)
            url = query.get("url", [""])[0]
            referer = query.get("referer", [""])[0]
            if not url:
                self._send_json({"error": "missing url"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                payload, suffix, content_type = _download_image(url, referer=referer)
            except Exception:
                self._send_json({"error": "image fetch failed"}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._send_image(payload, suffix, content_type)
            return
        if parsed.path == "/api/export":
          self._send_json({"error": "export is disabled"}, status=HTTPStatus.FORBIDDEN)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _chapters(self) -> list[Chapter]:
        if self.__class__.chapters_cache is None:
            self.__class__.chapters_cache = discover_chapters()
        return self.__class__.chapters_cache or []

    def _find_chapter(self, url: str) -> Chapter | None:
        for chapter in self._chapters():
            if chapter.url == url:
                return chapter
        return None

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_zip(self, payload: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", 'attachment; filename="combatron-chapter.zip"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_image(self, payload: bytes, suffix: str, content_type: str | None = None) -> None:
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        detected_type = content_type or mime_map.get(suffix.lower(), "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", detected_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(payload)

    def _chapter_zip(self, chapter: Chapter) -> bytes:
      pages = fetch_chapter_pages(chapter)
      buffer = BytesIO()
      with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for index, image_url in enumerate(pages.image_urls, start=1):
          image_bytes, extension, _ = _download_image(image_url)
          archive.writestr(f"{_slugify(chapter.title)}/page-{index:03d}{extension}", image_bytes)
        archive.writestr(
          f"{_slugify(chapter.title)}/manifest.json",
          json.dumps({"title": chapter.title, "url": chapter.url, "pages": list(pages.image_urls)}, indent=2).encode("utf-8"),
        )
      return buffer.getvalue()


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value.lower() or "chapter"


def _normalize_image_url(url: str) -> str:
    if "blogger.googleusercontent.com" in url:
        return re.sub(r"/s\d+(?:-[a-z])?/", "/s0/", url, count=1)
    return url


def _download_image(url: str, referer: str | None = None) -> tuple[bytes, str, str | None]:
    url = _normalize_image_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CombatronReader/0.1",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": referer or "https://projectcombatron.blogspot.com/",
    }
    request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        payload = response.read()
        content_type = response.headers.get_content_type()
    extension = re.search(r"\.(jpe?g|png|gif|webp)(?:$|[?#])", url, re.IGNORECASE)
    suffix = f".{extension.group(1).lower()}" if extension else ".jpg"
    if suffix == ".jpg" and content_type == "image/jpeg":
        suffix = ".jpeg"
    return payload, suffix, content_type


def run_server(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), CombatronHandler)
    print(f"Combatron Reader running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()