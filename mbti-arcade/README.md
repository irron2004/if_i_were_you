# 360Me (Perception Gap)

"If I were you" 관점에서 Self vs Others 인식 차이를 비교하는 웹 서비스입니다.

## ✨ 주요 기능

### 🔍 심리 검사 서비스
- **MBTI 성격 유형**: 개인 테스트 및 친구 평가 모드
- **상대방 입장에서 평가**: "내가 000 이라고 생각하고 MBTI를 작성해주세요"
- **실제 MBTI 비교**: "000의 실제 MBTI는 무엇인가요?" 기능
- **향후 추가 예정**: 에니어그램, 사랑의 언어, 스트레스 지수, 자기효능감, 감정 지능

## 🚀 빠른 시작

### 방법 1: 실행 스크립트 사용 (권장)

#### Windows Command Prompt
```cmd
# 배치 파일 실행
run.bat
```

#### Windows PowerShell
```powershell
# PowerShell 스크립트 실행
.\run.ps1
```

### 방법 2: Makefile 사용

#### Linux/macOS
```bash
# 도움말 보기
make help

# 전체 개발 환경 설정
make setup

# 서버 실행
make run
```

#### Windows (Make 설치 필요)
```cmd
# 도움말 보기
make help

# 전체 개발 환경 설정
make setup

# 서버 실행
make run
```

### 방법 3: 수동 실행

#### 1. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Windows Command Prompt:
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate
```

#### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

#### 3. 서버 실행
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📱 접속 방법

서버가 실행되면 다음 URL로 접속할 수 있습니다:

- **메인 페이지**: http://localhost:8000
- **MBTI 테스트**: http://localhost:8000/mbti
- **친구 MBTI 평가**: http://localhost:8000/mbti/friend

## 🛠️ 개발 도구

### Makefile 명령어

#### 개발 환경 설정
```bash
make install     # 의존성 설치
make venv        # 가상환경 생성
make setup       # 전체 개발 환경 설정
```

#### 서버 실행
```bash
make run         # 개발 서버 실행 (포트 8000)
make dev         # 개발 서버 실행 (포트 8001)
make prod        # 프로덕션 서버 실행
```

#### 테스트
```bash
make test        # 테스트 실행
make test-verbose # 상세한 테스트 실행
```

#### Docker
```bash
make docker-build # Docker 이미지 빌드
make docker-run   # Docker 컨테이너 실행
make docker-stop  # Docker 컨테이너 중지
make docker-clean # Docker 이미지 및 컨테이너 정리
```

#### 유틸리티
```bash
make clean       # 캐시 파일 정리
make format      # 코드 포맷팅
make lint        # 코드 린팅
make check       # 코드 품질 검사
```

## 🐳 Docker 실행

### Docker 이미지 빌드
```bash
docker build -t mbti-arcade .
```

### Docker 컨테이너 실행
```bash
docker run -p 8000:8000 mbti-arcade
```

## 📁 프로젝트 구조

```
mbti-arcade/
├── app/
│   ├── main.py              # FastAPI 애플리케이션
│   ├── database.py          # 데이터베이스 관리
│   ├── models.py            # Pydantic 모델
│   ├── routers/
│   │   ├── mbti.py         # MBTI 관련 라우터
│   ├── static/             # 정적 파일
│   └── templates/          # HTML 템플릿
├── requirements.txt         # Python 의존성
├── Makefile                # 개발 도구
├── run.bat                 # Windows 배치 파일
├── run.ps1                 # PowerShell 스크립트
├── Dockerfile              # Docker 설정
└── README.md               # 프로젝트 문서
```

## 🔧 기술 스택

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS (Tailwind CSS), JavaScript
- **Database**: 인메모리 데이터베이스 (JSON 파일 저장)
- **Template Engine**: Jinja2
- **Development**: Uvicorn, pytest

## 🧪 테스트

```bash
# 테스트 실행
python test_mbti.py

# 또는 Makefile 사용
make test
```

## 📝 주요 기능 설명

### MBTI 친구 평가 모드
1. **친구 정보 입력**: 이름, 이메일, "내가 000 이라고 생각하고 MBTI를 작성해주세요" 입력
2. **상대방 입장에서 평가**: 친구의 관점에서 MBTI 질문에 답변
3. **결과 확인**: 평가 결과와 통계 확인
4. **실제 MBTI 입력**: "000의 실제 MBTI는 무엇인가요?" 섹션에서 실제 MBTI 입력
5. **비교 분석**: 평가된 MBTI와 실제 MBTI 비교

### 네비게이션
- **핵심 동선**: Self 테스트 → 초대 링크 생성 → 결과 확인
- **모바일 반응형**: 모바일에서도 사용하기 편한 메뉴

## 🤝 기여하기

1. 이 저장소를 포크합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🆘 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 다른 포트로 실행
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 의존성 문제가 있는 경우
```bash
# 의존성 재설치
pip install -r requirements.txt --force-reinstall
```

### 가상환경 문제가 있는 경우
```bash
# 가상환경 삭제 후 재생성
rm -rf venv
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.

---

360Me - Self vs Others 인식 차이를 비교해보세요.
