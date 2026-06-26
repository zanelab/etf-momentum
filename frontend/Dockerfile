FROM node:24-alpine

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml .npmrc ./

ENV PNPM_CONFIG_MINIMUM_RELEASE_AGE=0 \
    PNPM_CONFIG_DANGEROUSLY_ALLOW_ALL_BUILDS=true

# pnpm 11 requires explicit build approval; for Docker dev image we allow all builds.
# Lockfile is still pinned via pnpm-lock.yaml; only postinstall scripts are approved.
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
