FROM node:20-alpine

WORKDIR /app

ENV API_PROXY_TARGET=http://backend:8000

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy application source
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
