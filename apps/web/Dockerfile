FROM node:20-alpine

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile=false

COPY . .

RUN pnpm build

CMD ["sh", "-c", "pnpm start -p ${PORT:-3000}"]
