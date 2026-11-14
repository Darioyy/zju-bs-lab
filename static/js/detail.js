const requestId = params.get('id');
const box = document.getElementById('detail');
let current = null; // 当前显示的单据，操作时要用它的 version

function infoList(r) {
  const rows = [
    ['类型', TEXT.type[r.type]],
    ['申请人', `${r.applicant_name}（${r.department_name}）`],
    ['创建时间', formatTime(r.created_at)],
  ];
  if (r.submitted_at) rows.push(['提交时间', formatTime(r.submitted_at)]);
  if (r.leave) {
    rows.push(
      ['请假类型', TEXT.kind[r.leave.kind]],
      ['日期', `${r.leave.start_date} 至 ${r.leave.end_date}`],
      ['天数', `${r.leave.days} 天`],
      ['事由', r.leave.reason],
    );
  }
  if (r.expense) {
    rows.push(
      ['报销类别', TEXT.category[r.expense.category]],
      ['金额', formatMoney(r.expense.amount)],
      ['事由', r.expense.reason],
    );
  }
  return el('dl', { class: 'info' }, rows.map(([k, v]) => [el('dt', {}, k), el('dd', {}, v)]));
}

const APPROVER = { manager: '部门经理', finance: '财务', admin: '管理员' };

function approverText(s) {
  return s.approver_name ? `${APPROVER[s.approver]} ${s.approver_name}` : APPROVER[s.approver];
}

// 流程条：提交 → 第 1 级 → 第 2 级。每一级该谁审由后端按 workflow.py 算好放在 steps 里，
// 这里只根据状态和这一轮的审批记录标出哪一级审完了、停在哪一级
function flowBar(r) {
  // 只看当前这一轮。之前被驳回的几轮在下面的审批记录里；草稿还没开始这一轮
  const records = r.status === 'draft' ? [] : r.approvals.filter((a) => a.round === r.round);
  const nodes = [el('span', { class: 'step ' + (r.status === 'draft' ? 'current' : 'done') },
    '提交', r.status !== 'draft' && ' ✓')];
  let waiting = null;
  for (const s of r.steps) {
    const record = records.find((a) => a.step === s.step);
    let node;
    if (record && record.decision === 'approve') {
      // 审过的写实际审批的人，管理员代审时和原定的审批人不一样
      node = el('span', { class: 'step done' }, record.approver_name, ' ✓');
    } else if (record) {
      node = el('span', { class: 'step rejected' }, record.approver_name, ' 驳回');
    } else if (r.status === 'pending' && s.step === r.current_step) {
      waiting = approverText(s);
      node = el('span', { class: 'step current' }, waiting);
    } else {
      node = el('span', { class: 'step' }, approverText(s));
    }
    nodes.push(el('span', { class: 'arrow' }, '→'), node);
  }
  return el('div', { class: 'flow' }, nodes, waiting && el('span', { class: 'note' }, `等${waiting}审批`));
}

function historyTable(r) {
  if (r.approvals.length === 0) return el('div', { class: 'empty' }, '还没有审批记录');
  return el('table', {},
    el('thead', {}, el('tr', {}, ['提交', '级', '审批人', '结果', '意见', '时间'].map((h) => el('th', {}, h)))),
    el('tbody', {}, r.approvals.map((a) => el('tr', {},
      el('td', {}, `第 ${a.round} 次`),
      el('td', {}, `第 ${a.step} 级`),
      el('td', {}, a.approver_name),
      el('td', {}, el('span', { class: 'badge ' + (a.decision === 'approve' ? 'approved' : 'rejected') },
        TEXT.decision[a.decision])),
      el('td', {}, a.comment || '-'),
      el('td', {}, formatTime(a.created_at)),
    ))));
}

// 按后端给的 actions 决定显示哪些按钮
function actionArea(r) {
  const has = (action) => r.actions.includes(action);
  const parts = [];

  const buttons = el('div', { class: 'buttons' },
    has('submit') && el('button', { class: 'primary', onclick: () => act('submit') }, '提交审批'),
    has('edit') && el('button', { onclick: () => { location.href = 'form.html?id=' + r.id; } }, '修改'),
    has('delete') && el('button', { class: 'danger', onclick: removeDraft }, '删除'),
    has('withdraw') && el('button', { onclick: () => act('withdraw', {}, '确定撤回这张申请？') }, '撤回'),
    has('reopen') && el('button', { onclick: reopen }, '修改后重新提交'),
  );
  if (buttons.children.length > 0) parts.push(buttons);

  if (has('approve')) {
    parts.push(
      el('h2', {}, '审批'),
      el('form', { id: 'decision-form', class: 'card', onsubmit: (e) => e.preventDefault() },
        el('div', { class: 'field' },
          el('textarea', { name: 'comment', maxlength: 500, placeholder: '审批意见，驳回时必填' }),
          el('div', { class: 'error-text', 'data-error': 'comment' })),
        el('div', { class: 'buttons' },
          el('button', { type: 'button', class: 'primary', onclick: () => decide('approve') }, '通过'),
          el('button', { type: 'button', class: 'danger', onclick: () => decide('reject') }, '驳回'))),
    );
  }
  return parts;
}

function render(r) {
  current = r;
  box.replaceChildren(
    el('div', { class: 'toolbar' },
      el('h1', {}, `#${r.id} ${r.title}`),
      statusBadge(r.status)),
    flowBar(r),
    el('div', { class: 'card' }, infoList(r)),
    el('h2', {}, '审批记录'),
    el('div', { class: 'table-wrap' }, historyTable(r)),
    ...actionArea(r), // 返回的是数组，要展开；直接传数组会被当成文字显示
  );
}

async function reload() {
  render(await api('GET', '/requests/' + requestId));
}

function setBusy(busy) {
  for (const b of box.querySelectorAll('button')) b.disabled = busy;
}

async function handleError(err) {
  if (err.status === 409) {
    // 单子被别人改过了：刷新成最新的样子，按钮也跟着变
    await reload().catch(() => {});
    showMessage(err.message);
    return;
  }
  const form = document.getElementById('decision-form');
  if (err.status === 422 && form) showFieldErrors(form, err.fields);
  showError(err);
  setBusy(false);
}

async function act(action, extra = {}, confirmText = null) {
  if (confirmText && !confirm(confirmText)) return false;
  setBusy(true);
  hideMessage();
  try {
    render(await api('POST', `/requests/${requestId}/${action}`, { version: current.version, ...extra }));
    showMessage('操作成功', 'ok');
    return true;
  } catch (err) {
    await handleError(err);
    return false;
  }
}

function decide(decision) {
  const form = document.getElementById('decision-form');
  const comment = form.elements.comment.value.trim();
  if (decision === 'reject' && !comment) {
    showFieldErrors(form, { comment: '驳回必须填写理由' });
    return;
  }
  // 审完一张，导航栏的待审数量跟着变
  act(decision, { comment }, decision === 'approve' ? '确定通过？' : '确定驳回？')
    .then((ok) => ok && loadTodoCount());
}

async function reopen() {
  if (await act('reopen')) location.href = 'form.html?id=' + requestId;
}

async function removeDraft() {
  if (!confirm('确定删除这张草稿？删除后不能恢复。')) return;
  setBusy(true);
  try {
    await api('DELETE', `/requests/${requestId}?version=${current.version}`);
    location.href = 'index.html';
  } catch (err) {
    await handleError(err);
  }
}

initPage()
  .then(() => (requestId ? reload() : showMessage('缺少单据编号')))
  .catch(showError);
