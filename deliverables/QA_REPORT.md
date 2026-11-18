# Hello, Officer! — Where Is My Ball? 검수 보고

음성을 포함한 HELLO_OFFICER_40S.mp4를 제작했다.
비디오는 1920×1080, 30 fps, 1,200프레임, 40.000초다.
비디오 스트림, AAC 스트림과 컨테이너 모두 40.000초로 확인했다.
H.264, yuv420p, AAC 48 kHz 스테레오와 faststart를 적용했다.

## 실제 검증

| 검증 | 결과 | 관측과 근거 |
|---|---|---|
| 원본 PNG와 ZIP 보존 | PASS | READY 윤수 10개·경장 4개와 프로젝트 PNG 해시 일치. 원본 ZIP과 전체 압축 해제 결과 보존 |
| 기존 제작물 보존 | PASS | Kokoro WAV, script.json, script.txt, park.svg, bench.svg를 이전 편집 ZIP과 바이트 비교. 기존 7초 작업본은 ball-qa에 보존 |
| PNG 알파와 포즈 | PASS | 14개 RGBA의 실제 투명 영역 확인. 14개 포즈가 타임라인에 등장. 한 배역의 보이는 PNG 최대 1개 |
| 7초 캐릭터 적용본 | PASS | 13.3–20.3초, 1080p, 210프레임과 AAC. 전체 디코딩과 정상 속도 muted 재생 완료 |
| 최종 프레임과 인코딩 | PASS | tools/verify_video.py와 qa/final-video.json |
| 전체 디코딩 | PASS | FFmpeg -xerror 종료 코드 0 |
| 전체 MP4 재생 | PASS | Chromium에서 정상 속도로 0–40초 후 ended 확인, media 오류 없음 |
| 검은 프레임 | PASS | FFmpeg blackdetect에서 0.02초 이상 검은 구간 검출 없음 |
| 정지 프레임 시각 검수 | PASS | 최종 MP4를 1초 간격으로 40장 확인. 자막·캐릭터·소품과 장면 순서 확인 |
| 핵심 컷과 마지막 프레임 | PASS | 493–496, 558–561프레임의 경장→공→윤수 컷과 마지막 1199프레임 확인. 포즈 이중상과 검은 전환 프레임 없음 |
| 공 위치 | PASS | 같은 bench.svg의 공을 세계 좌표 (1589, 654)에 유지 |
| 자막과 대본 | PASS | 13개 큐의 영어·한국어 자막과 대본 일치. WAV 실제 길이로 비중첩 배치 |
| 복습과 끝 대사 | PASS | 원래 c03·c08 WAV 재사용. 여백 3.877초와 2.753초. 마지막 WAV가 39.347초에 끝나며 0.653초 여유 |
| 구간 이동 | PASS | 정순·역순 DOM 상태 일치. 39.95초에서 7개 시점으로 돌아온 무손실 캡처의 픽셀 차이 모두 0 |
| HTML 전체 재생 | PASS | 첫 재생 뒤 정상 속도로 40초 도달. 누락 자산·페이지 오류·외부 요청 없음 |
| 모바일 HTML | PASS | 412×915 안드로이드 Chromium 에뮬레이션에서 재생 아이콘 터치 후 영상·음성 시계 진행, 화면 너비 412 유지 |
| 발음·감정·음질 청취 | NOT_RUN | 사용자 지시에 따라 모델 오디오 입력·청취·음성 분석 생략 |
| 사람이 정상 속도 움직임을 시청 | NOT_RUN | 정상 속도 재생은 자동화로 확인. 시각 평가는 추출 정지 프레임과 전환 프레임을 이용 |
| 실제 갤럭시 | NOT_RUN | 실기 기기 접근 없음 |

PASS는 표에 적힌 관측 범위에 한정한다.
영어 발음, 윤수 이름의 발음과 화자의 감정 전달은 청취 검수 대상에 남아 있다.
표정과 시선은 제공된 PNG 포즈 범위로 연출했다. 눈동자·관절·음절 립싱크 리깅은 포함하지 않는다.

## 사용한 스킬과 수정

script-to-motion 설치 커밋은 8fc16eabd9bbe692722b9df8a10aab4988268585다.
설치 README, SKILL.md, scripts/new_project.mjs, references/player-api.md와 render.py --help를 확인했다.
기존 설치 환경을 사용하고 별도 프로젝트 사본에서 작업했다.

js/cast.js와 assets/characters에 READY PNG 14개를 연결했다.
몸 크기와 발 기준점은 CSS 배치 값으로 맞췄으며 PNG 파일 내용과 방향을 유지했다.
큰 포즈 변화는 반응 컷과 발견 컷으로 연결했다. Y10은 얼굴·상체 구도로 사용했다.
영어는 기존 로컬 Kokoro WAV를 유지하고 FFmpeg로 합성했다.
tools/build_audio.py는 프로젝트 전용 Kokoro 연결이며 Fish Audio의 기본 기능과 구별된다.
고정 화자는 af_nova와 am_michael이며 피치를 변조하지 않았다.

제공 render.py의 프레임별 시각 설정, 안정 캡처와 인코딩을 사용했다.
프로젝트 사본에 MOTION_RENDER_2D=1을 추가해 HTML/PNG 장면에서 시스템 Chromium CPU 합성 경로를 선택했다.
will-change로 생긴 반복 탐색의 가장자리 차이를 제거하고 무손실 캡처로 재시험했다.
js/player.js 사본에 첫 재생 터치와 visualViewport 기반 모바일 크기 맞춤을 적용했다.
최종 소스 해시는 qa/source-hashes.json에 있다. 전역 스킬 패키지는 유지했다.

## 제출과 재사용

HELLO_OFFICER_PROJECT.zip에는 HTML/CSS/JS, PNG 14개, WAV, 로컬 GSAP과 글꼴, 라이선스와 렌더 지침을 담았다.
Kokoro 모델과 Python 가상환경은 현재 클라우드에 준비되어 있으며 편집 ZIP에는 생성된 WAV를 포함했다.
각 라이선스는 SOURCES_AND_LICENSES.md에 기록했다.
STORYBOARD.md에는 대사 시각과 포즈·카메라 연결이 있다.
PREVIEW.jpg는 최종 MP4에서 추출한 8개 장면의 미리보기다.

사용자가 공개 업로드를 허용한 irewon1-lgtm/yoonsu-english-video의 hello-officer-40s-20261118 브랜치로 전달한다.
수령 링크의 응답과 다운로드 파일 해시는 업로드 후 확인한다.
