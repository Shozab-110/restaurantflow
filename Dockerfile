FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY scripts/build-assets.mjs scripts/build-assets.mjs
COPY templates templates
COPY assets assets
COPY static static
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 restaurantflow
COPY . .
COPY --from=assets /app/static /app/static
RUN mkdir -p /app/media /app/staticfiles && chown -R restaurantflow:restaurantflow /app
USER restaurantflow
EXPOSE 8000
CMD ["gunicorn", "restaurantflow.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
