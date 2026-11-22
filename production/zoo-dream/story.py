import json
from pathlib import Path
sc=[]; seq=0
def l(role,en,ko):
 global seq
 seq+=1
 return dict(id=f'z{seq:03}',role=role,en=en,ko=ko)
def scene(key,view,rows,icon=None):
 sc.append(dict(id=key,view=view,lines=rows,icon=icon,seconds=15))
def turn(n,q,k,a,t,icon=None,ask='teacher',model='three'):
 m=l(model,a,t)
 scene('turn_'+str(n),'practice',[l(ask,q,k),m,dict(id='cue',role='sheriff',en='Yoonsu, your turn.',ko='윤수야, 네 차례야.'),m,dict(id='pause'+str(n),role='pause',en=a,ko=t)],icon)
scene('arrival','wide',[l('teacher','Today our classroom is a zoo stage!','오늘 우리 교실은 동물원 무대예요!'),l('y','Mom, watch our show!','엄마, 우리 공연 보세요!'),l('mom','I’ll be watching from the back row.','엄마는 뒷줄에서 보고 있을게!')])
scene('families','audience',[l('mom','There are ten children on stage today.','오늘 무대에는 어린이가 열 명이구나.'),l('y','Look! Three brought a microphone!','보세요! 쓰리가 마이크를 가져왔어요!')])
scene('zoo_gate','zoo',[l('three','One, two, three! Welcome to the zoo show!','하나, 둘, 셋! 동물원 공연에 오신 걸 환영해요!'),l('sheriff','Three, check the sky before we start.','쓰리야, 시작하기 전에 하늘을 봐.'),l('three','Blue sky! No clouds today.','파란 하늘이야! 오늘은 구름이 없어.')],'sun')
turn(1,'How’s the weather?','날씨가 어때요?','It’s sunny today.','오늘은 맑아요.','sun')
turn(2,'What is your name?','이름이 뭐예요?','I am Yoonsu.','저는 윤수예요.','mic',model='sheriff')
scene('age','zoo',[l('three','Count my blocks. One, two, three!','내 블록을 세어 봐. 하나, 둘, 셋!'),l('three','For our zoo play, I’m three years old.','오늘 동물원 놀이에서 나는 세 살이야.'),l('sheriff','Try Three’s answer. Later, use your own age.','쓰리의 대답을 연습해 봐. 나중엔 네 나이로 말해 봐.')],'three')
turn(3,'How old are you?','몇 살이에요?','I am three.','저는 세 살이에요. (쓰리 역할)','three')
turn(4,'Where do you go?','어디에 가요?','To the zoo!','동물원에 가요!','zoo')
scene('animals','zoo',[l('y','I go to the zoo. Who’s on stage?','저는 동물원에 가요. 무대에는 누가 있죠?'),l('three','A chicken and a duck! Listen to their sounds.','닭과 오리야! 소리를 들어 봐.'),l('three','Cluck, cluck! Quack, quack!','꼬꼬댁! 꽥꽥!')],'chicken')
turn(5,'Who says cluck, cluck?','누가 꼬꼬댁 울어요?','It’s a chicken.','닭이에요.','chicken')
turn(6,'Who says quack, quack?','누가 꽥꽥 울어요?','It’s a duck.','오리예요.','duck')
scene('music','zoo',[l('three','Time for our dream song. I’ll count us in!','우리의 꿈 노래 시간이야. 내가 박자를 셀게!'),l('three','One, two, three!','하나, 둘, 셋!'),l('y','I have a dream.','저에게는 꿈이 있어요.'),l('y','I like to sing a song.','저는 노래 부르는 걸 좋아해요.'),l('y','So I want to be a singer.','그래서 가수가 되고 싶어요.')],'mic')
turn(7,'What do you like to do on stage?','무대에서 무엇을 좋아해요?','I like singing.','노래 부르기를 좋아해요.','mic')
turn(8,'What do you want to be?','무엇이 되고 싶어요?','A singer, too!','저도 가수요!','mic')
scene('kitchen','zoo',[l('three','The singers are hungry. Who has a second dream?','노래한 친구들이 배고프대. 두 번째 꿈이 있는 사람?'),l('y','I also want to be a cook.','저는 요리사도 되고 싶어요.'),l('three','Here’s a pot. Let’s make soup for the show!','여기 냄비가 있어. 공연 친구들에게 수프를 만들어 주자!')],'pot')
turn(9,'What else do you want to be?','또 무엇이 되고 싶어요?','A cook, too!','요리사도요!','pot')
turn(10,'What shall we make together?','함께 무엇을 만들까요?','Let’s make soup.','수프를 만들어요.','pot')
scene('hands_up','child',[l('teacher','Who wants to ask a friend about their dream?','친구에게 꿈을 물어보고 싶은 사람?'),l('y','My hand is up!','저 손 들었어요!'),l('teacher','Go ahead, Yoonsu. Pass the question to Three.','좋아요, 윤수. 쓰리에게 질문해 봐요.'),l('y','How about you?','너는 어때?')],'mic')
turn(11,'Ask Three about her dream.','쓰리의 꿈을 물어봐요.','How about you?','너는 어때?','mic',model='sheriff')
scene('encore','zoo',[l('three','Me? I want to sing with you!','나? 너와 같이 노래하고 싶어!'),l('three','I have a dream.','저에게는 꿈이 있어요.'),l('three','I like to sing a song.','노래 부르기를 좋아해요.'),l('y','So I want to be a singer.','그래서 가수가 되고 싶어요.'),l('three','I also want to be a cook.','저는 요리사도 되고 싶어요.'),l('sheriff','How about you?','너는 어때?')],'mic')
scene('drawing','zoo',[l('y','Hi! This is my zoo picture.','안녕! 이건 내 동물원 그림이야.'),l('y','I am happy. I love my mom.','저는 행복해요. 우리 엄마를 사랑해요.'),l('three','Look at Mom smiling behind the children.','어린이들 뒤에서 엄마가 미소 짓고 있어.')],'heart')
turn(12,'How do you feel after your show?','공연이 끝나니 기분이 어때요?','I am happy.','저는 행복해요.','heart')
scene('clap','audience',[l('teacher','A big hand for our dream show!','우리의 꿈 공연에 큰 박수를 보내요!'),l('mom','I heard you sing, and I heard your question.','윤수 노래도 듣고 친구에게 묻는 말도 들었어.'),l('y','The duck sang along!','오리도 따라 불렀어요!'),l('mom','Quack, quack! I love you, too.','꽥꽥! 엄마도 사랑해.')])
Path('script.json').write_text(json.dumps(dict(title='쓰리와 윤수의 동물원 꿈 공연',en='The Zoo Dream Show',fps=24,scenes=sc),ensure_ascii=False,indent=2)+'\n')
