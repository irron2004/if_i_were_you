# Web Service Hub - Docker 통합 배포 가이드

## 🚀 개요

이 프로젝트는 여러 웹 서비스를 하나의 도메인에서 관리하는 통합 웹 서비스 허브입니다. Nginx 리버스 프록시를 사용하여 경로 기반 라우팅을 제공합니다.

## 📁 프로젝트 구조

```
web_service/
├── docker-compose.yml          # Docker Compose 설정
├── nginx/                      # Nginx 리버스 프록시 설정
│   ├── nginx.conf             # 메인 Nginx 설정
│   └── conf.d/
│       └── default.conf       # 서버 라우팅 설정
├── main-service/              # 메인 허브 서비스
├── math-app/                  # (제거됨) → calculate_math/frontend 참고
├── mbti-arcade/              # 360Me (perception gap) 서비스
└── calculate_math/            # (2025-10) 별도 저장소 → https://github.com/irron2004/calculate_math
```

## 🌐 서비스 라우팅

하나의 도메인에서 경로 기반으로 서비스에 접근할 수 있습니다:

- **메인 허브**: `http://yourdomain.com/` 또는 `http://localhost/`
- **MBTI 검사**: `http://yourdomain.com/mbti` 또는 `http://localhost/mbti`

## 🛠️ 설치 및 실행

### 1. 사전 요구사항

- Docker
- Docker Compose

### 2. 프로젝트 클론 및 실행

```bash
# 프로젝트 디렉토리로 이동
cd web_service

# Docker Compose로 모든 서비스 실행
docker-compose up --build
```

### 3. 서비스 접속

실행 후 다음 URL로 접속할 수 있습니다:

- **메인 허브**: http://localhost
- **MBTI 검사**: http://localhost/mbti

## 🔧 서비스 구성

### Nginx 리버스 프록시

- **포트**: 80 (HTTP), 443 (HTTPS)
- **역할**: 모든 요청을 적절한 서비스로 라우팅
- **설정**: `nginx/nginx.conf` 및 `nginx/conf.d/default.conf`

### 메인 허브 (main-hub)

- **포트**: 8080 (내부)
- **역할**: 중앙 허브 페이지 제공
- **기술**: FastAPI + Jinja2Templates

### MBTI (mbti-arcade)

- **기술**: FastAPI + Jinja2Templates
- **경로**: `/mbti` (MBTI 검사)

## 🔄 개발 모드

개발 중에는 볼륨 마운트를 통해 코드 변경사항이 즉시 반영됩니다:

```bash
# 개발 모드로 실행 (볼륨 마운트 활성화)
docker-compose up --build
```

## 🐛 문제 해결

### 1. 포트 충돌

다른 서비스가 80번 포트를 사용 중인 경우:

```bash
# 포트 확인
netstat -an | findstr :80

# 다른 포트로 변경 (docker-compose.yml 수정)
ports:
  - "8080:80"  # 80 대신 8080 사용
```

### 2. 빌드 오류

```bash
# 캐시 삭제 후 재빌드
docker-compose down
docker system prune -f
docker-compose up --build
```

### 3. 권한 문제 (Linux/Mac)

```bash
# nginx 설정 파일 권한 설정
chmod 644 nginx/nginx.conf
chmod 644 nginx/conf.d/default.conf
```

## 📝 환경 변수

### 도메인 설정

프로덕션 환경에서는 `nginx/conf.d/default.conf`의 `server_name`을 실제 도메인으로 변경하세요:

```nginx
server {
    listen 80;
    server_name yourdomain.com;  # 실제 도메인으로 변경
    # ...
}
```

### HTTPS 설정

SSL 인증서를 추가하려면:

1. SSL 인증서 파일을 `nginx/ssl/` 디렉토리에 배치
2. `nginx/conf.d/default.conf`에 SSL 설정 추가
3. `docker-compose.yml`에 SSL 볼륨 마운트 추가

## 🚀 프로덕션 배포

### 1. 도메인 설정

```nginx
# nginx/conf.d/default.conf
server {
    listen 80;
    server_name yourdomain.com;  # 실제 도메인
    # ...
}
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
DOMAIN=yourdomain.com
ENVIRONMENT=production
```

### 3. 배포 실행

```bash
# 프로덕션 모드로 실행
docker-compose -f docker-compose.yml up -d
```

## 📊 모니터링

### 로그 확인

```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs nginx
docker-compose logs main-hub
```

### 헬스 체크

```bash
# 메인 허브 헬스 체크
curl http://localhost/health

# 각 서비스 헬스 체크
curl http://localhost/mbti/health
```

## 🔒 보안 고려사항

1. **HTTPS 강제**: 프로덕션에서는 HTTPS 리다이렉트 설정
2. **방화벽**: 필요한 포트만 열기
3. **업데이트**: 정기적인 보안 업데이트
4. **백업**: 데이터베이스 및 설정 파일 정기 백업

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 
