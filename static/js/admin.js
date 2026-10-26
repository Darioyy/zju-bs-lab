// 管理部门和用户，只有管理员能进。点表格的一行编辑，「新建」按钮新建

const deptForm = document.getElementById('dept-form');
const userForm = document.getElementById('user-form');
const passwordForm = document.getElementById('password-form');

let me = null;
let departments = [];
let users = [];
let editingDept = null; // 正在编辑的部门，新建时为 null
let editingUser = null;

const toId = (value) => (value === '' ? null : Number(value));

function options(select, items, selected) {
  select.replaceChildren(...items.map(([value, text]) =>
    el('option', { value, selected: String(value) === String(selected ?? '') }, text)));
}

async function load() {
  [departments, users] = await Promise.all([api('GET', '/admin/departments'), api('GET', '/admin/users')]);
  renderDepartments();
  renderUsers();
}

function done(text) {
  deptForm.hidden = true;
  userForm.hidden = true;
  passwordForm.hidden = true;
  showMessage(text, 'ok');
  return load();
}

function setBusy(form, busy) {
  for (const b of form.querySelectorAll('button')) b.disabled = busy;
}

// 发请求；422 把原因显示在对应输入框下面，其他错误显示在页面顶部
async function send(form, method, path, body, okText) {
  setBusy(form, true);
  hideMessage();
  try {
    await api(method, path, body);
    await done(okText);
  } catch (err) {
    if (err.status === 422) showFieldErrors(form, err.fields);
    showError(err);
  } finally {
    setBusy(form, false);
  }
}

// 部门 ------------------------------------------------------------------

function renderDepartments() {
  document.getElementById('dept-rows').replaceChildren(...departments.map((d) =>
    el('tr', { class: 'link', onclick: () => editDept(d) },
      el('td', {}, d.id),
      el('td', {}, d.name),
      el('td', {}, d.manager_name || '-'),
      el('td', {}, d.member_count),
    )));
}

function editDept(d) {
  editingDept = d;
  hideMessage();
  showFieldErrors(deptForm, {});
  document.getElementById('dept-form-title').textContent = d ? '编辑部门：' + d.name : '新建部门';
  deptForm.elements.name.value = d ? d.name : '';
  // 新部门还没有人，建好、调人进来以后再指定经理
  document.getElementById('manager-field').hidden = !d;
  if (d) {
    const members = users.filter((u) => u.department_id === d.id && u.is_active);
    options(deptForm.elements.manager_id,
      [['', '不设经理'], ...members.map((u) => [u.id, `${u.display_name}（${u.username}）`])], d.manager_id);
  }
  deptForm.hidden = false;
  deptForm.scrollIntoView({ block: 'nearest' });
  deptForm.elements.name.focus();
}

function saveDept() {
  const name = deptForm.elements.name.value.trim();
  if (!name) {
    showFieldErrors(deptForm, { name: '不能为空' });
    return;
  }
  if (editingDept === null) {
    send(deptForm, 'POST', '/admin/departments', { name }, '部门已新建，调人进来以后可以指定经理');
  } else {
    send(deptForm, 'PUT', '/admin/departments/' + editingDept.id,
      { name, manager_id: toId(deptForm.elements.manager_id.value) }, '已保存');
  }
}

// 用户 ------------------------------------------------------------------

function departmentText(u) {
  if (u.department_id === null) return '-';
  return u.manages ? `${u.department_name}（经理）` : u.department_name;
}

function renderUsers() {
  document.getElementById('user-rows').replaceChildren(...users.map((u) =>
    el('tr', { class: u.is_active ? 'link' : 'link inactive', onclick: () => editUser(u) },
      el('td', {}, u.username),
      el('td', {}, u.display_name),
      el('td', {}, TEXT.role[u.role]),
      el('td', {}, departmentText(u)),
      el('td', {}, u.is_active ? '在职' : '已停用'),
      el('td', {}, u.id !== me.id && el('button', {
        class: u.is_active ? 'link danger' : 'link',
        onclick: (e) => { e.stopPropagation(); toggleActive(u); },
      }, u.is_active ? '停用' : '启用')),
    )));
}

function editUser(u) {
  editingUser = u;
  hideMessage();
  showFieldErrors(userForm, {});
  showFieldErrors(passwordForm, {});
  document.getElementById('user-form-title').textContent = u ? `编辑用户：${u.display_name}` : '新建用户';
  const f = userForm.elements;
  f.username.value = u ? u.username : '';
  f.username.disabled = !!u; // 账号建好后不能改
  f.display_name.value = u ? u.display_name : '';
  options(f.role, Object.entries(TEXT.role), u ? u.role : 'staff');
  options(f.department_id,
    [['', '无（只有管理员可以不属于部门）'], ...departments.map((d) => [d.id, d.name])],
    u ? u.department_id : (departments[0] && departments[0].id));
  f.password.value = '';
  document.getElementById('initial-password-field').hidden = !!u;
  passwordForm.elements.password.value = '';
  passwordForm.hidden = !u;
  userForm.hidden = false;
  userForm.scrollIntoView({ block: 'nearest' });
  (u ? f.display_name : f.username).focus();
}

// 和后端 accounts.py、schemas.py 的规则一致，后端还会再查
function validateUser(body) {
  const errors = {};
  if (body.username !== undefined && !/^[a-z0-9_]{3,32}$/.test(body.username)) {
    errors.username = '3~32 位小写字母、数字或下划线';
  }
  if (!body.display_name) errors.display_name = '不能为空';
  if (body.role !== 'admin' && body.department_id === null) errors.department_id = '普通员工和财务必须属于一个部门';
  if (body.password !== undefined && body.password.length < 6) errors.password = '至少 6 个字符';
  return errors;
}

function saveUser() {
  const f = userForm.elements;
  const body = {
    display_name: f.display_name.value.trim(),
    role: f.role.value,
    department_id: toId(f.department_id.value),
  };
  if (editingUser === null) {
    body.username = f.username.value.trim();
    body.password = f.password.value;
  }
  const errors = validateUser(body);
  showFieldErrors(userForm, errors);
  if (Object.keys(errors).length > 0) return;

  if (editingUser === null) {
    send(userForm, 'POST', '/admin/users', body, `已新建用户 ${body.username}`);
  } else {
    send(userForm, 'PUT', '/admin/users/' + editingUser.id, body, '已保存');
  }
}

function resetPassword() {
  const password = passwordForm.elements.password.value;
  if (password.length < 6) {
    showFieldErrors(passwordForm, { password: '至少 6 个字符' });
    return;
  }
  if (!confirm(`确定重置 ${editingUser.display_name} 的密码？`)) return;
  send(passwordForm, 'POST', `/admin/users/${editingUser.id}/password`, { password }, '密码已重置');
}

async function toggleActive(u) {
  const action = u.is_active ? 'deactivate' : 'activate';
  if (u.is_active && !confirm(`确定停用 ${u.display_name}？停用后不能登录，已登录的也会退出。`)) return;
  hideMessage();
  try {
    await api('POST', `/admin/users/${u.id}/${action}`);
    await done(u.is_active ? `已停用 ${u.display_name}` : `已启用 ${u.display_name}`);
  } catch (err) {
    showError(err);
  }
}

// ----------------------------------------------------------------------

document.getElementById('dept-new').addEventListener('click', () => editDept(null));
document.getElementById('dept-save').addEventListener('click', saveDept);
document.getElementById('dept-cancel').addEventListener('click', () => { deptForm.hidden = true; });
document.getElementById('user-new').addEventListener('click', () => editUser(null));
document.getElementById('user-save').addEventListener('click', saveUser);
document.getElementById('user-cancel').addEventListener('click', () => {
  userForm.hidden = true;
  passwordForm.hidden = true;
});
document.getElementById('password-save').addEventListener('click', resetPassword);
// 输入框里按回车也是保存，不让浏览器按默认方式提交表单
deptForm.addEventListener('submit', (e) => { e.preventDefault(); saveDept(); });
userForm.addEventListener('submit', (e) => { e.preventDefault(); saveUser(); });
passwordForm.addEventListener('submit', (e) => { e.preventDefault(); resetPassword(); });

async function init() {
  me = await initPage();
  if (me.role !== 'admin') {
    showMessage('只有管理员能进入这一页');
    return;
  }
  document.getElementById('departments').hidden = false;
  document.getElementById('users').hidden = false;
  await load();
}

init().catch(showError);
