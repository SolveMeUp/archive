# archive 배달용 이미지 = nginx + mkdocs 빌드 결과(정적 HTML).
# 본앱(Client)과 동일한 "이미지 빌드 → ghcr push → 서버 pull" 패턴(통일감).
# 앱 로직은 0 — 이미지는 그냥 정적 파일을 담는 택배 상자다.

# 1) Build stage — mkdocs 정적 사이트 빌드
FROM python:3.12-slim AS build
WORKDIR /app

# 의존성 먼저 복사 (레이어 캐시 최적화)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 소스(content/·mkdocs.yml·overrides/) 복사 후 빌드.
# --strict: 깨진 링크·nav 누락 등을 빌드 실패로 잡는다(CI 빌드 잡과 동일 계약).
COPY . .
RUN mkdocs build --strict

# 2) Run stage — nginx로 정적 서빙
FROM nginx:alpine
# 빌드 결과(site/)를 /archive/ 서브패스 밑에 둔다.
# mkdocs는 일반 페이지엔 상대경로 자산(assets/..., ../../assets/...)을, 404.html엔
# site_url 기반 절대경로(/archive/assets/...)를 쓴다. 둘 다 /archive/ prefix를
# 가정하므로 컨테이너 안에서도 같은 경로 밑에 있어야 참조가 깨지지 않는다.
COPY --from=build /app/site /usr/share/nginx/html/archive
COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
