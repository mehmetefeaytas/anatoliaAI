# Next.js dashboard + chatbot UI
#
# `NEXT_TELEMETRY_DISABLED=1` her aşamada: Next.js varsayılan olarak build ve
# çalışma zamanında anonim kullanım verisi gönderir. Projedeki tek somut
# telemetri açığı buydu — `Dockerfile.api` HF telemetrisini zaten kapatıyordu.
ARG NEXT_TELEMETRY_DISABLED=1

FROM node:20-alpine AS deps
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
# `npm install` DEĞİL `npm ci`: lockfile'a sadık kurulum, tekrar üretilebilir
# imaj. Lockfile imaja kopyalanmadığı için `ci` kullanılamıyordu.
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.js ./next.config.js
EXPOSE 3000
CMD ["npm", "start"]
