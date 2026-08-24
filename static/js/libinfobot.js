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

  const addMessage = (text, kind = 'bot', books = []) => {
    const item = document.createElement('div');
    item.className = `libinfobot-message ${kind}`;
    const avatar = kind === 'bot'
      ? '<span class="libinfobot-message-avatar" aria-hidden="true"><i class="bi bi-robot"></i></span>'
      : '';
    let html = `<div class="libinfobot-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;

    // Search results are deliberately display-only. Users can ask a follow-up
    // question in the chat instead of using crowded action buttons or links.
    if (Array.isArray(books) && books.length) {
      html += `<div class="libinfobot-results">${books.map((book) => {
        const title = escapeHtml(book.title || copyText('untitled', 'Untitled book'));
        const author = escapeHtml(book.author_name || copyText('author', 'Author unavailable'));
        return `<div class="libinfobot-result"><strong>${title}</strong><small>${author}</small></div>`;
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
      addMessage(answer, 'bot', Array.isArray(data.books) ? data.books : []);
    } catch (error) {
      showError(error.message || copyText('error', 'Something went wrong. Please try again.'));
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
})();
