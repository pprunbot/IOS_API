FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制应用文件
COPY app.py requirements.txt ./

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建工作目录并设置权限
RUN mkdir -p /app/site_sources && chmod -R 777 /app/site_sources

# 设置工作用户为非 root
USER user

# 暴露端口
EXPOSE 5000

# 启动应用程序
CMD ["python", "app.py"]


