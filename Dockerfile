FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-runtime.txt /app/requirements-runtime.txt
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app && mkdir /data && chown app:app /data
COPY examples/__init__.py /app/examples/__init__.py
COPY examples/catalog /app/examples/catalog
ENV DATABASE_URL=sqlite:////data/catalog.db
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "examples.catalog.main:app", "--host", "0.0.0.0", "--port", "8000"]
