FROM node:24-alpine AS cssbuild

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && \
    pnpm install

COPY ksp-naboj ./ksp-naboj
RUN pnpm run build
CMD ["pnpm", "run", "watch"]

FROM ghcr.io/trojsten/django-docker:v6

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY --chown=appuser:appuser . /app/
COPY --chown=appuser:appuser --from=cssbuild /app/ksp-naboj/styles/static/app.css /app/ksp-naboj/styles/static/app.js /app/ksp-naboj/styles/static/
RUN SECRET_KEY=none python manage.py collectstatic --no-input

ENV BASE_START=/app/start.sh
