"""One, Two and Three. Geometry and paint reconstructed from the official character plates."""
from functools import lru_cache
from math import cos, pi, sin

from design import ellipse, grad, group, path, raster, rect, svg, use

# Front, edge, back, limb, rim. The limbs and hands are continuous contours.
PALETTE = {
    1: ('#ff5551','#e62636','#9e1521','#8b1c28','#9d2026'),
    2: ('#ffc35b','#ff982e','#cf6823','#75467e','#8f507e'),
    3: ('#ffef61','#f6d12a','#b48c13','#aa3641','#d79719'),
}
UNIT=76
SIZE=(232,363)
ORIGIN=(116,337)

def eye(x,y,r,opening,gaze,role):
    ink=PALETTE[role][4]
    frame=ellipse(x,y,r+4,(r+5)*1.06,'url(#rim)',ink,1)
    if opening<.10:
        return frame+path(f'M{x-r+4} {y} Q{x} {y+5} {x+r-4} {y}','none','#581d32',3.1)
    w=r*max(.09,opening)
    iris=x+gaze*r*.31
    return frame+ellipse(x,y,r,w*1.07,'#fffdf8','#f8ead4',.7)+ellipse(iris,y+1,r*.49,w*.62,'#36273a')+ellipse(iris+.5,y+1,r*.42,w*.57,'#120f16')+ellipse(iris-r*.13,y-w*.30,r*.13,w*.13,'#fff9ef')

def face(role,phoneme,gaze,blink,nod,squint):
    if role==1:
        out=eye(1,27,22,1-blink,gaze,role)
        eye_shift=1
    else:
        y=24-nod*1.08
        r=17.8 if role==2 else 13.1
        out=path(f'M-40 {y-3} H40','none','#854c7f',8) if role==2 else ''
        out+=eye(-20,y,r,1-blink,gaze,role)+eye(20,y,r,1-blink,gaze,role)
        eye_shift=0
    y=57 if role==1 else 55
    rim={1:'#9f212a',2:'#ed715e',3:'#bd291f'}[role]
    w,h={'closed':(14,5.7),'M':(12,2.5),'E':(16,6.8),'A':(16,10),'O':(10,11),'F':(13,4.6)}.get(phoneme,(14,6))
    h+=squint*2
    if phoneme in ('M','closed') and squint<.3:
        return out+path(f'M-{w} {y} Q1 {y+12} {w} {y-2}','none',rim,3.0)
    x=eye_shift
    mouth=path(f'M{-w+x} {y-h*.55} Q{x} {y-h*.06} {w+x} {y-h*.66} Q{w*.91+x} {y+h} {x} {y+h} Q{-w*.94+x} {y+h} {-w+x} {y-h*.55}Z','#381522',rim,3.6)
    mouth+=ellipse(x,y+h*.53,w*.52,h*.30,'#de777d')
    if phoneme!='O':
        mouth+=path(f'M{-w*.8+x} {y-h*.40} Q{x} {y+h*.04} {w*.8+x} {y-h*.48} L{w*.59+x} {y+h*.22} Q{x} {y+h*.52} {-w*.64+x} {y+h*.19}Z','#fff4e6')
    return out+mouth

def capsule(start,end,z,hold=None):
    x,y=start;u,v=end
    elbow=(.45*x+.55*u+z[0],.45*y+.55*v+z[1])
    a=f'M{x} {y} Q{elbow[0]} {elbow[1]} {u} {v}'
    hand=ellipse(u,v,6.2 if hold else 6.7,8.5,'url(#limb)')
    if hold:
        hand+=ellipse(u+hold*3,v-4,4.1,4.3,'url(#limb)')
    return path(a,'none','url(#limb)',11.5)+hand

def foot(role,side,period,travel,lift,spread):
    x=side*19+spread*side
    stride=period*2*pi+(pi if side<0 else 0)
    tip=x+cos(stride)*travel
    y=-max(0,sin(stride))*lift
    form=path(f'M{x} -24 Q{x+3*side} {y-11} {tip} {y-3}','none','url(#limb)',12)
    if role==2:
        form+=rect(tip-6,y-10,12,5,'#fff0dd',1.7)
        form+=path(f'M{tip-10} {y-3} Q{tip-7} {y-10} {tip+3} {y-7} Q{tip+11} {y-6} {tip+12} {y+3} Q{tip+7} {y+6} {tip-10} {y+4}Z','#ef8f21','#cf661e',1.4)
        form+=path(f'M{tip-8} {y+4} H{tip+11}','none','#ac531d',2)
    else:
        form+=ellipse(tip,y-3,7.2,9.2,'url(#limb)')
    return form

def crown(wobble):
    piece=path('M-33 0 C-36-14 -47-24 -40-31 Q-23-29 -13-13 Q-11-33 0-39 Q11-33 13-13 Q23-29 41-31 C45-24 36-15 33 0 Z','url(#crown)','#991b27',1.1)
    for x,y in ((-40,-31),(0,-39),(41,-31)):
        piece+=ellipse(x,y,4.7,4.6,'url(#pearl)','#d89416',.9)
    return use(piece,0,1,1,wobble)

@lru_cache(140)
def draw(role,mouth,gaze,blink,phase,hop,lean,squash,yaw,gesture,target=None,performance="idle",progress=0):
    """A world-relative hand target is provided in local artwork coordinates."""
    body=role*UNIT
    f,edge,back,skin,rim=PALETTE[role]
    defs=(grad('front',f,edge)+grad('side',edge,back)+grad('top',f,edge)+
          grad('limb',rim if role==1 else skin,skin)+grad('rim',rim,skin)+
          grad('crown','#fb5057','#b9272c')+grad('pearl','#ffff8b','#edaa12')+grad('button','#fa6250','#b5191c'))
    # The three rigid block silhouettes retain their exact edge lengths.
    # Bend the short legs under the stack before takeoff and again on landing.
    settle=0.
    if performance=='hop':
        for center,width,depth in ((.17,.16,10),(.84,.16,8)):
            q=max(0.,1-abs(progress-center)/width)
            settle+=depth*q*q*(3-2*q)
    fy=-25-body+settle
    rise=role==1 or role==3
    feet=foot(role,-1,phase,hop*(10 if rise else 17),hop*(16 if rise else 8),gesture*2)
    feet+=foot(role,1,phase,hop*(10 if rise else 17),hop*(16 if rise else 8),gesture*2)
    if performance=='sit':
        seat=progress
        settle=10*seat
        fy+=settle
        feet=''
        for side in (-1,1):
            hip=side*19
            ankle=hip+23*seat
            sole=-3-8*seat
            feet+=path(f'M{hip} {-24+settle} Q{hip+3*side+15*seat} {-12-6*seat} {ankle} {sole}','none',skin,12)
            feet+=ellipse(ankle,sole,7.2+1.2*seat,9.2-1.6*seat,'url(#limb)')
    yaw=max(-.92,min(.92,yaw))
    w=37.4-abs(yaw)*3.8
    dep=yaw*24
    bias=-yaw*5.3
    blocks=[]
    for j in range(role):
        yy=fy+j*UNIT
        shift=lean*(role-j)*3.1
        block=path(f'M{-w} 0 L{-w+dep} -8 H{w+dep} L{w} 0Z','url(#top)',edge,1)
        side=w if dep>0 else -w
        block+=path(f'M{side} 0 L{side+dep} -8 V{UNIT-10} L{side} {UNIT-2}Z','url(#side)',back,.75)
        block+=rect(-w,0,w*2,UNIT-1.1,'url(#front)',5.9,edge,1.3)
        block+=path(f'M{-w+5} 5 Q{-w+3} 2 {-w+8} 2H{w-8}','none',f,1.5)
        if role==3 and j==1:
            for k in (17,37,57):
                block+=ellipse(bias+.7,k,6.5,6.8,'url(#button)','#c52b22',.65)
        blocks.append(use(block,shift,yy))
    arm_height=fy+(42 if role==1 else 97 if role==2 else 88)
    far_end=(-62-gesture*11,arm_height+26-gesture*(25+15*cos(phase*2*pi)))
    close_end=(61+gesture*10,arm_height+28-gesture*(29+11*sin(phase*2*pi)))
    if performance=='pass':
        near=sin(pi*progress)**2
        far_end=(-62-8*near,arm_height+26+16*near)
        close_end=(61+12*near,arm_height+28-30*near)
    elif performance=='wave':
        near=sin(pi*progress)**2
        close_end=(61+7*near,arm_height+28-66*near)
    arm0=capsule((-w+4,arm_height),target if target and target[0]<0 else far_end,(-5,11),-1 if target and target[0]<0 else None)
    arm1=capsule((w-4,arm_height),target if target and target[0]>=0 else close_end,(5,11),1 if target and target[0]>=0 else None)
    head=use(face(role,mouth,gaze,blink,gesture,gesture*.61),lean*role*3.1+bias,fy)
    top=use(crown(sin(phase*2*pi+.65)*gesture*3.5),lean*role*3.2,fy-5) if role==3 else ''
    digit_y=fy-(54 if role==3 else 16)
    label=f'<text x="{lean*role*2.4}" y="{digit_y}" text-anchor="middle" font-family="DejaVu Sans" font-size="30" font-weight="bold" fill="#211a24" stroke="#fff1cf" stroke-width="0.35">{role}</text>'
    # Modest squash is applied to the block column during actual landing.
    body_svg=group(arm0+''.join(blocks)+arm1+head+top+label,
                   f'translate(0 -25) scale(1 {1-squash*.065}) translate(0 25)')
    return raster(svg(feet+body_svg,*SIZE,defs,'-116 -337 232 363'),*SIZE)
