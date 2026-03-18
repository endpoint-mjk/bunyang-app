# 🏠 분양알리미 PWA

KB시세 기반 분양정보 자동 필터링 모바일 웹앱

## 🚀 배포 방법 (3가지)

---

### 방법 A: Vercel 배포 (추천, 1분)

1. GitHub에 이 폴더를 push

```bash
git init
git add .
git commit -m "분양알리미 PWA"
git remote add origin https://github.com/너의아이디/bunyang-app.git
git push -u origin main
```

2. [vercel.com](https://vercel.com) 접속 → GitHub 로그인
3. **"Import Project"** → 방금 만든 repo 선택
4. Framework: **Vite** 자동 감지됨 → **Deploy** 클릭
5. 30초 후 `https://bunyang-app.vercel.app` 같은 URL 생성

---

### 방법 B: Netlify 배포 (드래그 앤 드롭)

1. 로컬에서 빌드:
```bash
npm install
npm run build
```

2. [app.netlify.com/drop](https://app.netlify.com/drop) 접속
3. `dist` 폴더를 브라우저에 드래그 앤 드롭
4. 즉시 URL 생성

---

### 방법 C: 로컬에서 바로 테스트

```bash
npm install
npm run dev
```

터미널에 `http://localhost:5173` 표시됨 → 브라우저에서 열기

같은 와이파이에 있는 핸드폰에서 테스트하려면:
```bash
npm run dev -- --host
```
터미널에 `http://192.168.x.x:5173` 표시됨 → 핸드폰 브라우저에서 이 주소 입력

---

## 📱 핸드폰 홈 화면에 설치 (PWA)

배포 후 핸드폰 브라우저에서 URL 접속:

### iPhone (Safari)
1. 하단 공유 버튼 (↑ 아이콘) 탭
2. **"홈 화면에 추가"** 선택
3. **"추가"** 탭
4. 홈 화면에 앱 아이콘 생성 → 네이티브 앱처럼 동작

### Android (Chrome)
1. 주소창 옆 **⋮** 메뉴 탭
2. **"홈 화면에 추가"** 또는 **"앱 설치"** 선택
3. 홈 화면에 앱 아이콘 생성

---

## 📁 파일 구조

```
bunyang-pwa/
├── index.html              # HTML 진입점 (PWA 메타태그 포함)
├── package.json            # 의존성
├── vite.config.js          # Vite 설정
├── public/
│   ├── manifest.json       # PWA 매니페스트
│   ├── sw.js               # Service Worker (오프라인)
│   ├── icon-192.png        # 앱 아이콘
│   └── icon-512.png        # 앱 아이콘 (스플래시)
└── src/
    ├── main.jsx            # React 진입점
    └── App.jsx             # 앱 전체 코드
```
