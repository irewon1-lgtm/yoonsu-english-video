# 윤수의 놀이터 대작전 / Playground Pals

11분 1초, 1920×1080, 24fps. 여섯 놀이 장면에 세 단어 영어 발화가 총 36회 있다. 앱에서는 같은 예문을 두 번째 들은 뒤 윤수가 답할 때까지 기다린다. 다운로드용 MP4에는 매번 4초의 말하기 여백이 있다.

## 제작 원본

- script.json, timeline.json, Playground_English.srt — 최종 대사, 프레임 시간표, 영문 자막.
- sprites — 재생에 사용한 무손실 전신 시트, 셀 위치표, 전 프레임의 인물별 위치와 셀 번호.
- art.py, three, stage.py, sets — 캐릭터 전신 작화와 놀이터 무대. raw 이미지의 팔다리·입을 잘라 움직이는 방식 대신 좌표 경로로 매 자세의 완성 그림을 그린다.
- audio, mix.wav, effects.py — 대사별 단일 음성 WAV, 입모양 큐, 공·발의 접촉음과 최종 믹스.
- References.md — 전문 교육 자료와 적용한 동작.

Python 3.12, Pillow, NumPy, SciPy, FFmpeg, Cairo, librsvg, Noto CJK 글꼴 환경에서 재생성한다.

```sh
mkdir -p qa sprites delivery
python edit.py
python film.py atlas
python film.py render
```
