FROM python:3.12.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . /app
RUN useradd --create-home --uid 10001 coalicion && chown -R coalicion:coalicion /app
USER coalicion
ENV PYTHONPATH=/app
ENV COALICION_SERVICE=api
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"
ENTRYPOINT ["python","docker_entrypoint.py"]
