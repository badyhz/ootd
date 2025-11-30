# 使用官方 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码文件 (包括 templates 文件夹)
COPY . .

# 暴露端口
EXPOSE 80

# 启动命令 (使用 gunicorn 启动 Flask，更稳定)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "app:app"]