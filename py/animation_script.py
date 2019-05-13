import numpy as np 
import animations as A 


animations = {	
	'rand_drop' : A.GaussianDroplet(
						sigma=A.Signals("t") | A.Sin(hz=1) | A.Lin(shift=np.pi/8, mult=-np.pi/16),
						color=[A.Const(255), A.Signals("vol") | A.Lin(mult=255), A.Signals("pitch") | A.Lin(mult=255)], 
						pos=[A.Rand([-np.pi, np.pi]), A.Rand([0, np.pi])]
	),
	'pos_drop' : A.GaussianDroplet(
						sigma=A.Signals("t") | A.Sin(hz=0.5) | A.Lin(shift=np.pi/16, mult=-np.pi/16),
						color=[A.Const(1), A.Const(0), A.Const(0)], 
						pos=[A.Const(-np.pi/2), A.Const(np.pi/2)]
	),
	'uniform_rain' : A.GaussianRain(
						radius=A.Const(np.pi/16),
						color=[A.Signals("vol"), A.Const(0), A.Signals("rand")], 
						nr_droplets=5, 
						drop_duration=A.Const(1)
	),
	'theta_jiggle' : A.ThetaRing(
						width=A.Const(np.pi/16),
						color=[A.Const(1), A.Const(0), A.Const(1)], 
						pos=A.Const(np.pi/16)#A.Sin(hz=0.5) | A.Lin(shift=np.pi/4, mult=-np.pi/4)
	)
}

# for t in np.linspace(0, 1, 60):
# 	signals = {"t" : t, "vol" : t*2, "pitch" : t/2}
# 	print(t, gaussian_drop(signals).shape)

def get_pixels(signals, anim_name):
	return animations[anim_name](signals)