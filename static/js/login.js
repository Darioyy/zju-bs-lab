const form = document.getElementById('login-form');

// 登录后跳到哪里。只跳回本站的页面，不检查的话，别人可以发一个 login.html?next=https://坏网站 的链接。
// 不能只看是不是以 / 开头：浏览器把 /\坏网站 当成 //坏网站，也是外站。所以按浏览器的规则解析，再比较 origin
// 比较通过后跳完整地址，不只取路径：/.//坏网站 规范化后路径是 //坏网站，单独拿出来又成了外站
function nextPage() {
  const next = params.get('next');
  if (next) {
    try {
      const url = new URL(next, location.origin);
      if (url.origin === location.origin) return url.href;
    } catch (e) {
      // 不是合法的地址，当作没有
    }
  }
  return 'index.html';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  hideMessage();
  try {
    await api('POST', '/login', {
      username: form.username.value.trim(),
      password: form.password.value,
    });
    location.href = nextPage();
  } catch (err) {
    showMessage(err.message); // 这里的 401 是密码错，要显示出来，不能用 showError
    button.disabled = false;
  }
});
