(() => {
  'use strict';

  const root = document.querySelector('[data-libinfobot]');
  if (!root) return;

  const panel = root.querySelector('[data-libinfobot-panel]');
  const toggles = root.querySelectorAll('[data-libinfobot-toggle]');
  const form = root.querySelector('[data-libinfobot-form]');
  const input = root.querySelector('[data-libinfobot-input]');
  const messages = root.querySelector('[data-libinfobot-messages]');
  const typing = root.querySelector('[data-libinfobot-typing]');
  const errorBox = root.querySelector('[data-libinfobot-error]');
  const sendButton = root.querySelector('[data-libinfobot-send]');
  const clearButton = root.querySelector('[data-libinfobot-clear]');
  const initialMessagesHtml = messages.innerHTML;
  const copy = (() => {
    try { return JSON.parse(root.dataset.libinfobotCopy || '{}'); }
    catch (_) { return {}; }
  })();
  const copyText = (key, fallback) => copy[key] || fallback;
  let requestInFlight = false;

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  const setOpen = (open) => {
    panel.hidden = !open;
    toggles.forEach((toggle) => toggle.setAttribute('aria-expanded', String(open)));
    if (open) window.setTimeout(() => input.focus(), 80);
  };

  const scrollMessages = () => { messages.scrollTop = messages.scrollHeight; };

  const renderRichText = (value) => {
    const lines = String(value ?? '').split(/\r?\n/);
    return lines.map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return '<span class="libinfobot-rich-spacer" aria-hidden="true"></span>';
      let safe = escapeHtml(trimmed).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      if (/^(?:[-*•]\s+)/.test(trimmed)) {
        safe = safe.replace(/^[-*•]\s+/, '');
        return `<div class="libinfobot-rich-list-item"><span aria-hidden="true">•</span><span>${safe}</span></div>`;
      }
      return `<p>${safe}</p>`;
    }).join('');
  };

  const renderBookCards = (books) => `<div class="libinfobot-book-cards">${books.map((book) => {
    const title = escapeHtml(book.title || copyText('untitled', 'Untitled book'));
    const author = escapeHtml(book.author_name || copyText('author', 'Author unavailable'));
    const category = escapeHtml(book.category_name || copyText('category', 'Library book'));
    const available = Number(book.available_copies || 0) > 0;
    const availability = copyText(available ? 'available' : 'unavailable', available ? 'Available' : 'Currently unavailable');
    const id = Number(book.book_id);
    const action = Number.isFinite(id)
      ? `<button type="button" class="libinfobot-card-action" data-libinfobot-view="${id}">${copyText('view_details', 'View details')}</button>`
      : '';
    return `<article class="libinfobot-book-card"><div class="libinfobot-book-card-main"><strong>${title}</strong><small>${author}</small><div class="libinfobot-book-meta"><span class="libinfobot-category-badge">${category}</span><span class="libinfobot-availability ${available ? 'is-available' : 'is-unavailable'}"><i aria-hidden="true"></i>${escapeHtml(availability)}</span></div></div>${action}</article>`;
  }).join('')}</div>`;

  const renderPdfSummaryCard = (text) => `<section class="libinfobot-summary-card"><div class="libinfobot-summary-title"><i class="bi bi-stars" aria-hidden="true"></i><strong>${copyText('pdf_summary_title', 'AI Summary')}</strong></div><div class="libinfobot-summary-content">${renderRichText(text)}</div><button type="button" class="libinfobot-copy-summary" data-libinfobot-copy-summary><i class="bi bi-copy" aria-hidden="true"></i>${copyText('copy_summary', 'Copy summary')}</button></section>`;

  const addMessage = (text, kind = 'bot', books = [], intent = '') => {
    const item = document.createElement('div');
    item.className = `libinfobot-message ${kind}`;
    const avatar = kind === 'bot'
      ? '<span class="libinfobot-message-avatar" aria-hidden="true"><img src="/static/images/pumub-libinfobot-logo.png" alt=""></span>'
      : '';
    let html = `<div class="libinfobot-bubble">${intent === 'PDF_SUMMARY' ? renderPdfSummaryCard(text) : renderRichText(text)}</div>`;

    if (Array.isArray(books) && books.length) {
      html += renderBookCards(books);
    }

    item.innerHTML = avatar + html;
    messages.appendChild(item);
    scrollMessages();
  };

  const setLoading = (loading) => {
    typing.hidden = !loading;
    input.disabled = loading;
    sendButton.disabled = loading;
    if (loading) scrollMessages();
  };

  const showError = (message) => {
    errorBox.textContent = message;
    errorBox.hidden = false;
  };

  const ask = async (question) => {
    const trimmed = String(question || '').trim();
    if (!trimmed || requestInFlight) return;
    requestInFlight = true;
    errorBox.hidden = true;
    addMessage(trimmed, 'user');
    setLoading(true);
    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ question: trimmed })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || copyText('error', 'LibInfoBot could not answer right now.'));
      const answer = data.answer || data.summary || (data.status === 'not_found'
        ? copyText('no_book', 'I could not find a matching book in the library database.')
        : copyText('no_answer', 'I could not find an answer in the authorized library data.'));
      addMessage(answer, 'bot', Array.isArray(data.books) ? data.books : [], data.intent || '');
    } catch (error) {
      showError(error.message || copyText('error', 'Something went wrong. Please try again.'));
    } finally {
      requestInFlight = false;
      setLoading(false);
      input.focus();
    }
  };

  const clearHistory = async () => {
    const confirmed = window.confirm(copyText('clear_confirm', 'Clear this chat history?'));
    if (!confirmed || requestInFlight) return;
    clearButton.disabled = true;
    errorBox.hidden = true;
    try {
      const response = await fetch('/api/ai/clear-history', {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        credentials: 'same-origin'
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || copyText('error', 'Could not clear chat history.'));
      messages.innerHTML = initialMessagesHtml;
      input.value = '';
      scrollMessages();
      addMessage(copyText('clear_done', 'Chat history cleared.'), 'bot');
    } catch (error) {
      showError(error.message || copyText('error', 'Could not clear chat history.'));
    } finally {
      clearButton.disabled = false;
      input.focus();
    }
  };

  if (clearButton) clearButton.addEventListener('click', clearHistory);
  toggles.forEach((toggle) => toggle.addEventListener('click', () => setOpen(panel.hidden)));
  messages.addEventListener('click', (event) => {
    const viewButton = event.target.closest('[data-libinfobot-view]');
    if (viewButton) {
      const bookId = Number(viewButton.dataset.libinfobotView);
      if (Number.isInteger(bookId) && bookId > 0) window.location.assign(`/student/book/${bookId}`);
      return;
    }
    const copyButton = event.target.closest('[data-libinfobot-copy-summary]');
    if (copyButton) {
      const card = copyButton.closest('.libinfobot-summary-card');
      const summary = card?.querySelector('.libinfobot-summary-content')?.innerText?.trim() || '';
      if (!summary) return;
      const copied = () => {
        copyButton.classList.add('is-copied');
        copyButton.innerHTML = `<i class="bi bi-check2" aria-hidden="true"></i>${copyText('summary_copied', 'Summary copied')}`;
        window.setTimeout(() => {
          copyButton.classList.remove('is-copied');
          copyButton.innerHTML = `<i class="bi bi-copy" aria-hidden="true"></i>${copyText('copy_summary', 'Copy summary')}`;
        }, 1800);
      };
      if (navigator.clipboard?.writeText) navigator.clipboard.writeText(summary).then(copied).catch(() => {});
      else copied();
    }
  });

  root.querySelectorAll('[data-libinfobot-quick]').forEach((button) => {
    button.addEventListener('click', () => ask(button.dataset.question || ''));
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const question = input.value;
    input.value = '';
    ask(question);
  });
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
})();
