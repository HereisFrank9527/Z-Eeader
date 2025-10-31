# 项目基于的python版本
FROM python:3.11.13
# 将当前目录复制到镜像的指定目录下（这里选择的是docker_flask目录）
ADD . /z-reader
# 项目的工作路径
WORKDIR /z-reader
# 导入项目依赖包（就是刚刚编写的requirements.txt）
# -i https://mirrors.aliyun.com/pypi/simple/是指定国内镜像加速下载依赖
RUN pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
# 端口5000 (设置你的项目的服务端口)
EXPOSE 5000
# 执行
CMD ["python", "./app.py", "0.0.0.0"]
