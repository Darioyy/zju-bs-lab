const form = document.getElementById('login-form');

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
    // 只跳回本站的路径。不检查的话，别人可以发一个 login.html?next=https://坏网站 的链接
    const next = params.get('next');
    location.href = next && next.startsWith('/') && !next.startsWith('//') ? next : 'index.html';
  } catch (err) {
    showMessage(err.message); // 这里的 401 是密码错，要显示出来，不能用 showError
    button.disabled = false;
  }
});
