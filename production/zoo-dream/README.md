# 쓰리와 윤수의 동물원 꿈 공연

5분 14초, 1920×1080, 24fps. 교실에서 동물원 공연을 열고 꿈 노래를 부른다. 영어 발화 차례는 12회다. MP4의 4초 여백에서 따라 말할 수 있고, 앱은 같은 지점에서 답을 기다린다.

편집 원본에 최종 WAV, 입 모양 큐, 자막, 전신 스프라이트, 교실과 무대 배경이 들어 있다. FFmpeg, Noto CJK 글꼴과 requirements.txt의 Python 의존성을 설치하고 실행한다.

```sh
mkdir -p delivery qa
python edit.py
python render.py --build-sprites
python render.py --jobs 4
```

쓰리 원화를 다시 만들 때는 make_art.py를 사용한다. finish_sound.py는 합성 직후의 대사를 노래 음높이로 바꾸는 도구다. 동봉된 최종 음성은 이미 처리되어 있다.
