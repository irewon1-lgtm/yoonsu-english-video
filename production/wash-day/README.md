# 윤수의 뽀득뽀득 씻기 클럽 · v11
## 파일 열기
스프라이트 ZIP만 받아도 동작을 볼 수 있습니다. ZIP 전체를 풀고 같은 폴더의 ‘원화 보기.html’을 엽니다. 배경색을 바꾸거나 이전·다음 자세로 넘길 수 있습니다. HD 전신 셀은 1024×1024 출력본입니다. 개별 원화의 실제 작업 해상도는 각 JSON의 native_working_cell 항목에 있습니다. 근접 동작·걷기·친구 시트의 크기는 검수기에서 연 시트별로 다릅니다.

## 본편 수정
편집 프로젝트, 스프라이트, 소품과 발가락 접사 ZIP을 같은 빈 폴더에 풉니다. 각 ZIP 안의 photo 디렉터리가 합쳐져야 합니다. 추가 원화 ZIP은 색상과 실루엣을 다시 편집할 때 사용합니다.
- film.py에서 카메라와 합성 순서를, coverage.py에서 컷 시점을 편집합니다.
- timeline.json의 시간 단위는 24fps의 프레임입니다. episode.turns는 초 단위입니다. Wash_Day.srt는 영어 자막입니다.
- audio 폴더에는 대사 WAV가 한 목소리씩 들어 있습니다. wash-mix.wav가 본편과 같은 48kHz 모노 믹스입니다.
- photo/v11/body/body_motion.py에 전신 원화의 실제 노출 순서가 있습니다. photo/v11/portrait/face.py에는 윤수의 음소별 표정과 눈 감는 시점이 있습니다.
- photo/v11/macro의 README.md에 소품을 다시 렌더하는 방법과 모델 출처가 있습니다. 검수 도판과 작가 및 보건기관 출처는 ‘동작 비교’ PDF에 있습니다.

Python 3, Cairo, FFmpeg, 글꼴 DejaVu Sans 및 URW Bookman이 필요합니다. 아래 명령은 압축을 푼 프로젝트 폴더에서 실행합니다.

```sh
python -m pip install -r requirements.txt
python film.py --frame 1228 --width 1920 --out rinse.png
python film.py --jobs 2
python verify.py
```

전체 렌더 결과는 The_Squeaky_Clean_Club.mp4입니다. 웹 사진첩의 마이크와 음성 인식은 album-web/voice.js와 player.js에 있습니다. 웹 재생과 원격 업데이트에 사용하는 앱 코드는 기존 yoonsu-english-video 저장소에서 이어서 관리합니다.

## 다른 작업 환경에서 이어가기
이 폴더는 사진첩 배포본의 Python 렌더러와 타임라인을 보관합니다. 소유자의 Google Drive에서 “윤수 · 뽀득뽀득 씻기 클럽 · 동작 수정 v11” 폴더를 열고 Wash_v11_Edit.zip, Yoonsu_Wash_v11_Sprites.zip, Wash_v11_Props.zip, Wash_v11_Toe.zip을 여기에 함께 풉니다. 원본 원화에서 다시 편집할 때는 Wash_v11_Art_1.zip과 Wash_v11_Art_2.zip도 풉니다. 발가락 접사의 편집 씬은 photo/v11/toe_contact/toe-contact.blend입니다.
