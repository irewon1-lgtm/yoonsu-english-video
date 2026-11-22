# 좋은 아침, 어린이집 가자! · 2D 스프라이트 수정본

본편은 3분 27초, 1920×1080, 24fps다. 윤수의 연습 문장 15회와 각각 3초의 답변 여백, 이야기 속 추가 영어 대사 10개를 넣었다.

## 편집 원본 열기

편집 ZIP, 스프라이트 ZIP 01·02·03을 같은 폴더에 푼다. 04_Brush ZIP을 마지막에 풀고 같은 이름의 파일은 덮어쓴다. `exposures.csv`에서 어떤 원화가 화면에 나타나는지 프레임별로 확인할 수 있다. 각 동작의 `index.json`에 노출 길이와 이동 순서가 있다. `overrides/wake`, `overrides/shoes`, `overrides/depart`에는 투명 스프라이트시트와 저장된 전신 셀이 들어 있다. `overrides/dialogue`에는 카메라가 정렬된 대사 장면 원화가 있다.

## 영상 재생성

FFmpeg·FFprobe와 Python 3이 필요하다. Python 의존성은 `requirements.txt`에 있다.

- 본편 영상은 `python film.py --jobs 4`로 만든다.
- 한 장면 확인은 `python film.py --frame 400 --out sample.png`를 실행한다.
- 동작 검수 영상은 `python film.py --gate --out Animation_Check_2D_1080p.mp4`로 만든다.
- 음성이나 대사를 수정했으면 `python edit.py`로 WAV와 자막, 사진첩 `data.js`를 갱신한다.
- 본편은 `python verify_sprite.py Good_Morning_Yoonsu_2D_Sprites_1080p.mp4`로 검사한다.

재생 면에는 완성된 등록 셀 한 장을 표시한다. 별도의 사람과 배경 층이 있는 셀은 원래 고정 좌표로 먼저 합쳐진다. 대사 컷은 몸과 얼굴, 입모양이 함께 그려져 있다. 행동 시작과 끝, 손과 물건의 접촉, 움직임에 쓰는 두 프레임 기본 노출을 시간표에 기록했다. [동작 참고](References.md)

이 저장소에는 편집 코드와 타임라인이 있다. 사진, 원화, 녹음은 별도 편집 ZIP과 스프라이트 ZIP에서 불러온다.
