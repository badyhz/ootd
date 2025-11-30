# 使用官方 Python 基础镜像
FROM python:3.9-slim

# 【新增】安装系统证书，解决 SSL 报错问题
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码文件
COPY . .

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "app:app"]
