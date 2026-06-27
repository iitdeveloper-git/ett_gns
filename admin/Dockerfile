FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
ARG NEXT_PUBLIC_GNS_API_URL
ENV NEXT_PUBLIC_GNS_API_URL=${NEXT_PUBLIC_GNS_API_URL}
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/out ./out
EXPOSE 3000
CMD ["serve", "-s", "out", "-l", "3000"]
