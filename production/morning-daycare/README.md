# 좋은 아침, 어린이집 가자! / Good Morning, Yoonsu!

작업 폴더는 `production/morning-daycare/`에 대응합니다. 재생기는 기존 사진첩과 같은 `turns` 및 `repeatStarts`를 사용합니다.

## 폴더 구성

- `story.json`과 `dialogue.json`에는 15장면의 행동, 복장, 가방 위치, 대사와 반응을 기록합니다.
- `actions/*/index.json`의 순서와 정수 프레임 노출로 각 동작을 재생합니다. `cels/`는 실제 출력에 연결한 원화입니다. 촬영 배경과 분리된 원화, 혹은 가림이 합쳐진 원화를 클립의 기록에 표시합니다.
- `timeline.json`은 실제 녹음 길이로 생성한 통합 타임라인입니다. 편집 프로그램에서 쓸 자막은 `Good_Morning_Yoonsu_English.srt`입니다. `data.js`는 기존 사진첩과 연결할 좌표입니다.
- `audio/`는 개별 화자 WAV, `lips.json`은 Rhubarb의 입모양과 시간, `mix.wav`는 실제 마스터용 모노 WAV입니다.
- `QA_Summary.md`와 `reviews/`는 검사 상태와 결과입니다.

## 다시 실행

Python 3, Cairo, FFmpeg, DejaVu Sans, URW Bookman, Noto Sans CJK KR을 사용합니다.
알파 시트는 각 셀의 trim 위치와 원래 캔버스 크기를 적용해 복원합니다.

```sh
python -m pip install -r requirements.txt
python edit.py
python film.py --gate
python verify.py --gate
python film.py --frame 4132 --width 1920 --out example.png
python film.py --jobs 3
python verify.py
```

`--pieces 2,11,12`으로 지정한 장면만 업데이트할 수 있습니다. 렌더러와 원화, 장면 타이밍의 일치 여부를 장면마다 확인하며 현재 버전의 모든 장면이 있어야 최종 MP4를 조립합니다.

## 전달 ZIP 풀기

`Good_Morning_Yoonsu_Project.zip`과 같은 이름의 `Project_Art_*.zip`을 모두 한 폴더에 풉니다. `Sprites.zip`과 `Sprites_Part_*.zip`은 원화 인덱스와 프레임을 따로 모아 볼 때 같은 폴더에 풉니다. 본편을 렌더하는 데는 프로젝트 묶음이 필요합니다. `editor/`의 OpenRaster 세 파일은 본편의 실제 접촉 포즈에서 배경과 동작 셀을 분리한 Krita·GIMP용 스냅숏입니다.

소유자의 개인 보관 폴더 ‘좋은 아침, 어린이집 가자! · 영상과 제작 원본’에서 프로젝트 ZIP 묶음을 내려받아 풉니다. 원음과 레이어 원화, 사적 공간의 배경은 해당 ZIP에서 제공합니다. 기존 사진첩과 출시 목록은 별도로 관리합니다.
