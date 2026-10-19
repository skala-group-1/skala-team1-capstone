# 빌드 컨텍스트는 저장소 루트 (backend 와 같은 방식):
#   docker build -f frontend/Dockerfile .
#   compose: build: { context: ., dockerfile: frontend/Dockerfile }
# 타입체크가 src/mocks 의 data/mock/out/*.json import 를 확인하므로 mock 데이터도 복사한다 (운영 번들에는 포함되지 않음)
FROM node:22-alpine AS build
WORKDIR /repo/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY data/mock/out/ /repo/data/mock/out/
# 운영 이미지는 항상 실제 backend 사용
ENV VITE_USE_MSW=false
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
EXPOSE 80
