const filter = document.getElementById('status-filter');
const tbody = document.querySelector('tbody');

for (const [value, text] of Object.entries(TEXT.status)) {
  filter.append(el('option', { value }, text));
}

async function load() {
  const query = filter.value ? '?status=' + filter.value : '';
  const rows = await api('GET', '/requests' + query);
  tbody.replaceChildren(...rows.map((r) =>
    el('tr', { class: 'link', onclick: () => { location.href = 'detail.html?id=' + r.id; } },
      el('td', {}, '#' + r.id),
      el('td', {}, TEXT.type[r.type]),
      el('td', {}, r.title),
      el('td', {}, statusBadge(r.status), ' ', progressText(r)),
      el('td', {}, formatTime(r.updated_at)),
    )));
  document.getElementById('empty').hidden = rows.length > 0;
}

filter.addEventListener('change', () => load().catch(showError));

initPage().then(load).catch(showError);
