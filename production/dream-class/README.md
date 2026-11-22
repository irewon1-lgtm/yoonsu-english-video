# I Have a Dream · 윤수의 꿈 발표

윤수가 친구들과 직업 그림 카드를 보고, 친구들 앞에서 꿈을 발표하는 4분 49초 참관 수업이다. 앱에는 세 단어 발화 차례가 열두 번 있다. 각 예문은 영어로 두 번 들려준다. 시청자가 자기 꿈을 말할 수 있다.

편집 원본 ZIP의 source, sets, sprites, icons, audio 폴더에 실제 영상과 음성에 사용한 자산이 있다. Python 의존성은 requirements.txt에 있다. FFmpeg와 Noto CJK 글꼴을 설치한 뒤 아래 명령으로 재생성한다.

```sh
mkdir -p qa delivery
python edit.py
python render.py --build-sprites
python render.py --jobs 4
```

수업 질문 참고 자료와 그림 저작자 표기는 References.md에 있다.
