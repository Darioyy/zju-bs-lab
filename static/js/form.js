// 新建和修改共用这一页：form.html 是新建，form.html?id=3 是修改 3 号草稿

const form = document.getElementById('request-form');
const field = (name) => form.elements[name];

let requestId = params.get('id') ? Number(params.get('id')) : null;
let version = null;
// 打开页面时生成一次。连点、网络重试发出的新建请求都带同一个值，后端只会建一张单
const clientKey = uuid4();

function switchType() {
  const type = field('type').value;
  document.getElementById('leave-fields').hidden = type !== 'leave';
  document.getElementById('expense-fields').hidden = type !== 'expense';
}

function collect() {
  const type = field('type').value;
  const body = { title: field('title').value.trim() };
  if (type === 'leave') {
    body.leave = {
      kind: field('leave.kind').value,
      start_date: field('leave.start_date').value,
      end_date: field('leave.end_date').value,
      days: field('leave.days').value.trim(),
      reason: field('leave.reason').value.trim(),
    };
  } else {
    body.expense = {
      category: field('expense.category').value,
      amount: field('expense.amount').value.trim(),
      reason: field('expense.reason').value.trim(),
    };
  }
  return body;
}

// 和后端的规则一致。前端先查一遍，用户马上能看到哪里填错；后端还会再查
function validate(body) {
  const errors = {};
  if (!body.title) errors.title = '不能为空';

  if (body.leave) {
    const { start_date: start, end_date: end, days, reason } = body.leave;
    if (!start) errors['leave.start_date'] = '必填';
    if (!end) errors['leave.end_date'] = '必填';
    if (start && end && end < start) errors['leave.end_date'] = '结束日期不能早于开始日期';
    const n = Number(days);
    if (!days || !(n > 0)) {
      errors['leave.days'] = '必须大于 0';
    } else if ((n * 2) % 1 !== 0) {
      errors['leave.days'] = '以 0.5 天为单位';
    } else if (start && end && end >= start) {
      const span = (Date.parse(end) - Date.parse(start)) / 86400000 + 1;
      if (n > span) errors['leave.days'] = `不能超过日期跨度 ${span} 天`;
    }
    if (!reason) errors['leave.reason'] = '不能为空';
  }

  if (body.expense) {
    const { amount, reason } = body.expense;
    const n = Number(amount);
    if (!amount || !(n > 0)) errors['expense.amount'] = '必须大于 0';
    else if (!/^\d+(\.\d{1,2})?$/.test(amount)) errors['expense.amount'] = '最多两位小数';
    else if (n > 100000) errors['expense.amount'] = '单笔不能超过 100000 元';
    if (!reason) errors['expense.reason'] = '不能为空';
  }
  return errors;
}

function setBusy(busy) {
  for (const b of form.querySelectorAll('button')) b.disabled = busy;
}

async function save(andSubmit) {
  const body = collect();
  const errors = validate(body);
  showFieldErrors(form, errors);
  if (Object.keys(errors).length > 0) return;

  setBusy(true);
  hideMessage();
  try {
    let detail;
    if (requestId === null) {
      const created = await api('POST', '/requests', { ...body, type: field('type').value, client_key: clientKey });
      requestId = created.id; // 记下来，提交失败后再点按钮就是修改，不会再新建
      detail = await api('GET', '/requests/' + requestId);
    } else {
      detail = await api('PUT', '/requests/' + requestId, { ...body, version });
    }
    version = detail.version;
    if (andSubmit) {
      await api('POST', `/requests/${requestId}/submit`, { version });
    }
    location.href = 'detail.html?id=' + requestId;
  } catch (err) {
    if (err.status === 422) showFieldErrors(form, err.fields);
    if (err.status === 409 && requestId !== null) {
      // 草稿已经被改过（比如在另一个标签页提交了），重新读一次版本号
      api('GET', '/requests/' + requestId).then((d) => { version = d.version; }).catch(() => {});
    }
    showError(err);
    setBusy(false);
  }
}

function fill(r) {
  field('type').value = r.type;
  field('type').disabled = true; // 类型建好后不能改
  field('title').value = r.title;
  if (r.leave) {
    for (const key of ['kind', 'start_date', 'end_date', 'reason']) field('leave.' + key).value = r.leave[key];
    field('leave.days').value = String(r.leave.days);
  } else {
    field('expense.category').value = r.expense.category;
    field('expense.amount').value = Number(r.expense.amount).toFixed(2);
    field('expense.reason').value = r.expense.reason;
  }
  switchType();
}

async function init() {
  const user = await initPage();
  if (user.department_id === null) {
    showMessage('管理员不属于任何部门，不能提交申请');
    setBusy(true);
    return;
  }
  if (requestId !== null) {
    document.getElementById('page-title').textContent = '修改申请 #' + requestId;
    const r = await api('GET', '/requests/' + requestId);
    if (!r.actions.includes('edit')) {
      showMessage(`这张单据当前是“${TEXT.status[r.status]}”，不能修改`);
      setBusy(true);
    }
    version = r.version;
    fill(r);
  } else {
    // toISOString 是 UTC 时间，早上 8 点前会变成昨天，所以用本地日期自己拼
    const d = new Date();
    const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    field('leave.start_date').value = today;
    field('leave.end_date').value = today;
  }
}

field('type').addEventListener('change', switchType);
document.getElementById('save-btn').addEventListener('click', () => save(false));
document.getElementById('submit-btn').addEventListener('click', () => save(true));

init().catch(showError);
