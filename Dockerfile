FROM python:3.12-slim

WORKDIR /srv

# 先只拷依赖清单再安装，代码改了重新构建时这一层能用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app
COPY static static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
