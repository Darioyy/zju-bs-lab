// 每个页面都先引入这个文件：请求后端、生成 DOM、导航栏、提示信息。

const TEXT = {
  type: { leave: '请假', expense: '报销' },
  status: { draft: '草稿', pending: '审批中', approved: '已通过', rejected: '已驳回', withdrawn: '已撤回' },
  kind: { annual: '年假', sick: '病假', personal: '事假' },
  category: { travel: '差旅', office: '办公用品', meal: '招待', other: '其他' },
  decision: { approve: '通过', reject: '驳回' },
  role: { staff: '普通员工', finance: '财务', admin: '管理员' },
};

const params = new URLSearchParams(location.search);

class ApiError extends Error {
  // detail 是一句话，或者是字段错误的列表（422），见后端 handlers.py
  constructor(status, detail) {
    let message = typeof detail === 'string' ? detail : `请求失败（${status}）`;
    if (Array.isArray(detail)) message = '输入有误，请检查标红的地方';
    super(message);
    this.status = status;
    this.fields = {};
    if (Array.isArray(detail)) {
      for (const e of detail) this.fields[e.loc.slice(1).join('.')] = e.msg;
    }
  }
}

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch('/api' + path, options);
  } catch (e) {
    throw new ApiError(0, '连不上服务器');
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (res.status === 401 && path !== '/login') {
    // 没登录或过期了，去登录，登录完再回到这一页
    location.href = 'login.html?next=' + encodeURIComponent(location.pathname + location.search);
  }
  if (!res.ok) throw new ApiError(res.status, data && data.detail);
  return data;
}

// el('a', { href: 'x.html', class: 'active' }, '文字', 子节点...)
// 文字一律作为文本节点插入，不会被当成 HTML 解析，用户填的内容里有 <script> 也只是显示出来
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

function showMessage(text, kind = 'error') {
  const box = document.getElementById('message');
  box.textContent = text;
  box.className = kind;
  window.scrollTo(0, 0);
}

function hideMessage() {
  document.getElementById('message').className = '';
}

function showError(err) {
  if (err.status === 401) return; // 已经在跳登录页了
  showMessage(err.message || String(err));
}

// 表单里每个输入框下面有 <div class="error-text" data-error="字段名">
function showFieldErrors(form, fields) {
  for (const box of form.querySelectorAll('[data-error]')) box.textContent = '';
  for (const input of form.querySelectorAll('.invalid')) input.classList.remove('invalid');
  for (const [name, msg] of Object.entries(fields)) {
    const box = form.querySelector(`[data-error="${name}"]`);
    if (box) box.textContent = msg;
    const input = form.elements[name];
    if (input) input.classList.add('invalid');
  }
}

function statusBadge(status) {
  return el('span', { class: 'badge ' + status }, TEXT.status[status]);
}

function progressText(r) {
  if (r.status !== 'pending') return '';
  return `第 ${r.current_step}/${r.total_steps} 级`;
}

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

function formatMoney(amount) {
  return Number(amount).toFixed(2) + ' 元';
}

// 防重复提交用的随机 id。crypto.randomUUID 只在 https 或 localhost 下能用，这里自己拼一个 v4 UUID
function uuid4() {
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

async function logout() {
  await api('POST', '/logout').catch(() => {});
  location.href = 'login.html';
}

// 取当前用户并画导航栏，没登录会被 api() 带到登录页
async function initPage() {
  const user = await api('GET', '/me');
  const here = location.pathname.split('/').pop() || 'index.html';
  const link = (href, text) => el('a', { href, class: href === here ? 'active' : null }, text);
  // append(null) 会插入文字“null”，所以先去掉不显示的项
  document.getElementById('nav').append(...[
    el('span', { class: 'brand' }, '审批系统'),
    link('index.html', '我的申请'),
    link('todo.html', '待我审批'),
    user.department_id !== null && link('form.html', '新建申请'),
    user.role === 'admin' && link('admin.html', '管理'),
    el('span', { class: 'spacer' }),
    el('span', { class: 'who' }, user.display_name),
    el('button', { class: 'link', onclick: logout }, '退出'),
  ].filter(Boolean));
  return user;
}
