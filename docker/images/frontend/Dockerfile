# 1. Use official Node.js image as base
FROM node:24-alpine AS builder
# 2. Set working directory
WORKDIR /app
# 3. Install dependencies (cached for rebuilds)
COPY docker/images/frontend/package*.json ./
COPY docker/images/frontend/tsconfig.json ./
RUN npm install
# 3. Code source Next.js
COPY docker/images/frontend/ ./
# 5. Build the Next.js app
RUN npm run build
# 6. Start from a fresh base image
FROM node:24-alpine AS runner
# Set environment variables
ENV NODE_ENV=production
# Set working directory
WORKDIR /app
# Copy only the built output and necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts
# 7. Expose port and start the server
EXPOSE 3000
CMD ["npm", "start"]