FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG BACKLINE_BUILD_SHA=development
ENV BACKLINE_BUILD_SHA=${BACKLINE_BUILD_SHA}
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
RUN mkdir -p /data && useradd -u 10001 -m backline && chown backline:backline /data
USER backline
ENV BACKLINE_DB=/data/backline.db
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn src.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
