# 윤수의 놀이터 대작전 / Playground Pals

11분 1초, 1920×1080, 24fps. 여섯 놀이 장면에 세 단어 영어 발화가 총 36회 있다. 앱에서는 같은 예문을 두 번째 들은 뒤 윤수가 답할 때까지 기다린다. 다운로드용 MP4에는 매번 4초의 말하기 여백이 있다.

## 제작 원본

- script.json, timeline.json, Playground_English.srt — 최종 대사, 프레임 시간표, 영문 자막.
- sprites — 재생에 사용한 무손실 전신 시트, 셀 위치표, 전 프레임의 인물별 위치와 셀 번호.
- redesign, cast, sets — 원화, 동작별 전신 그림, 배경 원화와 소품. cast는 실제 프레임을 다시 출력하는 데 필요한 등록된 전체 셀이다.
- art.py, grid.py, prepare_cast.py, stage.py — 전신 셀 선택, 시트 분리와 바닥 정렬, 배경 배치.
- audio, mix.wav, effects.py — 대사별 단일 음성 WAV, 입모양 큐, 공·발의 접촉음과 최종 믹스.
- References.md — 전문 교육 자료와 적용한 동작.

Python 3.12, Pillow, NumPy, SciPy, FFmpeg, Noto CJK 글꼴 환경에서 재생성한다.

```sh
mkdir -p qa sprites delivery
python film.py atlas
python film.py render
```
