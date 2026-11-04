FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 JOBHUNT_ENV=production JOBHUNT_DB=/data/jobhunt.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY jobhunter ./jobhunter
COPY data ./data
RUN useradd -m app && mkdir /data && chown app /data
USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1
# 웹: 기본. 봇은 `docker run ... python -m jobhunter.bot` 로 별도 컨테이너 실행
CMD ["python", "-m", "jobhunter.cli", "serve", "8000"]
