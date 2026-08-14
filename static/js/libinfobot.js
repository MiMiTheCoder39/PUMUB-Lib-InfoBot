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

  const addMessage = (text, kind = 'bot', books = []) => {
    const item = document.createElement('div');
    item.className = `libinfobot-message ${kind}`;
    const avatar = kind === 'bot' ? '<span class="libinfobot-message-avatar" aria-hidden="true"><i class="bi bi-robot"></i></span>' : '';
    let html = `<div class="libinfobot-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
    if (Array.isArray(books) && books.length) {
      html += `<div class="libinfobot-results">${books.map((book) => {
        const id = Number(book.book_id);
        const title = escapeHtml(book.title || 'Untitled book');
        const author = escapeHtml(book.author_name || 'Author unavailable');
        return `<div class="libinfobot-result"><strong>${title}</strong><small>${author}</small>${Number.isInteger(id) ? `<div class="libinfobot-result-actions"><button type="button" class="libinfobot-detail" data-action="book_information" data-book-id="${id}" data-book-title="${title}">Ask about this book</button><button type="button" class="libinfobot-detail" data-action="pdf_summary" data-mode="short" data-book-id="${id}" data-book-title="${title}">Short PDF summary</button><button type="button" class="libinfobot-detail" data-action="pdf_question" data-book-id="${id}" data-book-title="${title}">Ask about PDF</button></div>` : ''}</div>`;
      }).join('')}</div>`;
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

  const ask = async (question, bookId = null, action = null, mode = 'medium') => {
    const trimmed = String(question || '').trim();
    if (!trimmed || requestInFlight) return;
    requestInFlight = true;
    errorBox.hidden = true;
    addMessage(trimmed, 'user');
    setLoading(true);
    try {
      const payload = { question: trimmed };
      if (bookId) payload.book_id = bookId;
      if (action) payload.action = action;
      if (mode) payload.mode = mode;
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'LibInfoBot could not answer right now.');
      const answer = data.answer || data.summary || (data.status === 'not_found' ? 'I could not find a matching book in the library database.' : 'I could not find an answer in the authorized library data.');
      addMessage(answer, 'bot', Array.isArray(data.books) ? data.books : []);
    } catch (error) {
      showError(error.message || 'Something went wrong. Please try again.');
    } finally {
      requestInFlight = false;
      setLoading(false);
      input.focus();
    }
  };

  toggles.forEach((toggle) => toggle.addEventListener('click', () => setOpen(panel.hidden)));
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
  messages.addEventListener('click', (event) => {
    const button = event.target.closest('[data-book-id]');
    if (!button) return;
    const action = button.dataset.action || 'book_information';
    const bookId = Number(button.dataset.bookId);
    const title = button.dataset.bookTitle || 'this book';
    if (action === 'pdf_summary') {
      ask(`Summarize the PDF for “${title}”.`, bookId, action, button.dataset.mode || 'short');
    } else if (action === 'pdf_question') {
      ask(`What is this PDF about?`, bookId, action, 'medium');
    } else {
      ask(`Tell me about “${title}”.`, bookId, action, 'medium');
    }
  });
})();
