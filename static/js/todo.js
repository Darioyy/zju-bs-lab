async function load() {
  const rows = await api('GET', '/requests/todo');
  document.querySelector('tbody').replaceChildren(...rows.map((r) =>
    el('tr', { class: 'link', onclick: () => { location.href = 'detail.html?id=' + r.id; } },
      el('td', {}, '#' + r.id),
      el('td', {}, TEXT.type[r.type]),
      el('td', {}, r.title),
      el('td', {}, `${r.applicant_name}（${r.department_name}）`),
      el('td', {}, progressText(r)),
      el('td', {}, formatTime(r.submitted_at)),
    )));
  document.getElementById('empty').hidden = rows.length > 0;
}

initPage().then(load).catch(showError);
