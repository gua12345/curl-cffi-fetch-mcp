FROM python:3.12-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 直接安装 Python 依赖（curl-cffi 提供预编译 wheel，无需构建工具）
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 启动命令
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
