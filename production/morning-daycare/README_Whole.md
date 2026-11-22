# 좋은 아침, 어린이집 가자! · 전체 장면 스프라이트

## 원본 풀기

`Good_Morning_Yoonsu_Whole_Edit.zip`과 `Good_Morning_Yoonsu_Whole_Sprites*.zip`을 같은 빈 폴더에 푼다. `Whole_Cels*.zip`에는 사용한 개별 셀의 무손실 WebP가 들어 있다. 개별 셀 파일은 따로 열어 확인할 수 있다. 영상 재렌더에는 원본 스프라이트 시트를 사용한다.

## 타임라인 수정 및 렌더

Python에 Pillow와 cairocffi를 설치하고 FFmpeg를 실행 경로에 둔다. 1920×1080 본편을 만드는 명령은 `python film_whole.py --jobs 4`이다. 침실 프레임 515를 확인하려면 `python film_whole.py --frame 515 --out frame-515.png`를 실행한다. 핵심 동작 영상은 `python film_whole.py --gate --out Animation_Check_Whole.mp4`로 만든다.

`whole-scene.json`의 sheet와 셀 번호는 `assets/whole-scene/`의 실제 원화에 대응한다. 각 24fps 프레임은 장면 전체를 그린 셀 하나를 표시한다. `whole_exposures.csv`에는 노출을 시작한 프레임과 마지막 프레임 다음 경계가 있다. 영어 음성은 `audio/`의 WAV 원본과 마스터 `mix.wav`를 함께 보관한다.

사진첩에는 본편 MP4와 `data.js`를 함께 연결한다. 영어 자막의 편집본은 SRT로 제공한다.
