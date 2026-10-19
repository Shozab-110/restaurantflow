document.addEventListener('submit', (event) => {
  const form = event.target;
  if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
  // Delay until other validators (including the cart) have had a chance to reject submission.
  queueMicrotask(() => { if (!event.defaultPrevented) form.querySelectorAll('button[type="submit"],button:not([type])').forEach(b => { b.disabled = true; b.dataset.previousText = b.textContent; b.setAttribute('aria-busy', 'true'); }); });
});
document.addEventListener('htmx:responseError', () => { const el = document.getElementById('connection-error'); if (el) el.hidden=false; });
document.addEventListener('htmx:sendError', () => { const el = document.getElementById('connection-error'); if (el) el.hidden=false; });
document.addEventListener('htmx:afterSwap', () => { const el = document.getElementById('connection-error'); if (el) el.hidden=true; });
