# vim: set noet:ts=8:sw=8
# flake8: noqa

import numpy as np
import animations as A
import settings

def get_data():
    ooo_hue = A.SinT(hz=A.Signals('ooo_intensity')
                     | A.Lin(shift=0.1, mult=1)) | A.Lin(shift=0.5, mult=0.5)
    return dict(
        # animation=A.GaussianDroplet(
        #                 sigma=A.Signals("t") | A.Sin(hz=1) | A.Lin(shift=np.pi/12, mult=-np.pi/24),
        #                 color=[A.Signals("low"), A.Const(0), A.Const(0.5)], 
        #                 pos=[A.Const(0), A.Const(np.pi/2)]
        #                 ),

        # animation=A.GaussianRain(
        #                 radius=A.Const(np.pi/18),
        #                 color=[A.Const(1), A.Const(1), A.Const(1)], 
        #                 nr_droplets=2, 
        #                 drop_duration=A.Const(1)
        #                 ),

        # animation=A.FullOn(color=A.Hue(
        #     hue=A.Signals("t") | A.Sin(hz=4) | A.Lin(shift=0.5, mult=0.5),
        #     value=A.Signals("t") | A.Sin(hz=0.6) | A.Lin(shift=0.4, mult=0.1),
        # ))


        # animation=A.PhiRing(
        #     theta=A.Signals("t") | A.Sin(hz=0.5) | A.Lin(shift=-2, mult=np.pi/4),
        #     # theta=A.Signals("t") | A.Lin(mult=3),
        #     width=A.Const(0.3),
        #     color=A.Hue(
        #         hue=A.Signals("t") | A.Sin(hz=1) | A.Lin(shift=0.5, mult=0.5),
        #     )
        #     # color=A.Const((1, 0, 0))
        # ),


        sphere=A.Mixer(dict(
            std=A.Add(
                A.GaussianDroplet(
                    sigma=A.Signals('left_drone') | A.Lin(shift=0, mult=np.pi/40),
                    # sigma=A.Signals('left_drone') | A.Lin(shift=np.pi/100, mult=np.pi/50),
                    color=[A.Const(1), A.Const(0), A.Const(1)], 
                    pos=[A.Const(0), A.Const(np.pi/2)],
                ),
                A.GaussianDroplet(
                    sigma=A.Signals('right_drone') | A.Lin(shift=0, mult=np.pi/40),
                    color=[A.Const(1), A.Const(0), A.Const(1)], 
                    pos=[A.Const(1.3*np.pi/2), A.Const(np.pi/2)],
                ),
            ),
            ooo=A.FullOn(color=A.Hue(
                    # hue=A.Signals("t") | A.Sin(hz=0.2) | A.Lin(shift=0.5, mult=0.5),
                    hue=ooo_hue,
                    # hue=A.OooHue(),
                    value=A.Signals("loud"),
                )),
            test=A.Add(
                A.PhiRing(
                    width=np.pi/10,
                    color=[0.8, 0, 1],
                    theta=A.Signals('ring1') | A.Lin(mult=np.pi),
                ),
                A.PhiRing(
                    width=np.pi/10,
                    color=[1, 0, 0.8],
                    theta=A.Signals('ring2') | A.Lin(mult=np.pi/2),
                ),
            ),
            flash=A.FullOn(color=A.Hue(
                value=A.SinT(hz=A.Signals('loud') | A.Lin(shift=0, mult=8)) | A.Lin(shift=0.5, mult=0.5),
                saturation=A.Const(0),
            )),
        )),
        arms=[
            A.Mixer(dict(
                std=A.ArmGradient(
                    settings.arm_configs[i],
                    color=[1, 0, 1],
                    func=lambda x, signals=None: (1-x)**4,
                    # func=lambda x, signals=None: 1*(x < (
                    #     signals.get('right_drone' if i else 'left_drone', 0))),
                    mult=A.Signals('right_drone' if i else 'left_drone')#A.Signals("t") | A.Sin(hz=0.2) | A.Lin(shift=0.5, mult=0.5)
                    ),
                ooo=A.ArmGradient(settings.arm_configs[i], color=A.Hue(
                        # hue=A.SinT(hz=0.2) | A.Lin(shift=0.5, mult=0.5),
                        # hue=A.OooHue(),
                        hue=ooo_hue,
                        value=A.Signals("loud"),
                    ),
                    func=lambda x, signals=None: (1-x)**2,
                    ),
                test=A.Add(
                    A.ArmRing(
                        settings.arm_configs[i],
                        color=[0.8, 0, 1],
                        value=A.Signals('ring1') | A.Lin(shift=-1, mult=2),
                        width=0.1,
                        func=lambda d, signals: np.clip(d, 0, 1)**1.5 - 0.1,
                    ),
                    A.ArmRing(
                        settings.arm_configs[i],
                        color=[0.1, 0, 0.8],
                        value=A.Signals('ring2') | A.Lin(shift=-1, mult=2),
                        width=0.1,
                        func=lambda d, signals: np.clip(d, 0, 1)**1.5 - 0.1,
                    ),
                ),
                flash=A.ArmGradient(settings.arm_configs[i], color=A.Hue(
                    value=A.Signals('t') | A.Sin(hz=4) | A.Lin(shift=0.5, mult=0.5),
                    saturation=A.Const(0),
                    ),
                    # func=lambda x, signals=None: (1-x)**1,
                ),
            ))
            for i in range(len(settings.arm_configs))
            # A.ArmGradient(settings.arm_configs[0], color=[1, 0, 0], func=lambda x: x**3),
            # A.ArmFullOn(settings.arm_configs[0], color=[1, 0, 0]),
            # A.ArmGradient(settings.arm_configs[1], color=[0, 0, 1], func=lambda x: x**4),
        ],
        animation2=A.Add(
            A.PhiRing(
                theta=A.Signals("t") | A.Sin(hz=0.1) | A.Lin(shift=-2, mult=np.pi/4),
                width=A.Const(0.3),
                color=A.Const((1, 0, 0)),
            ),
            A.PhiRing(
                theta=A.Signals("t") | A.Sin(hz=0.2) | A.Lin(shift=-2, mult=np.pi/4),
                width=A.Const(0.3),
                color=A.Const((0, 0, 1)),
            ),
            # A.PhiRing(
            #     theta=A.Signals("t") | A.Sin(hz=0.45) | A.Lin(shift=-2, mult=np.pi/4),
            #     width=A.Const(0.3),
            #     color=A.Const((0, 1, 0)),
            # ),
        ),


        # animation= A.ThetaRing(
        #                 width=A.Const(np.pi/32),
        #                 color=[A.Const(1), A.Const(0), A.Const(0)], 
        #                 pos=A.Const(np.pi/16)#A.Sin(hz=0.5) | A.Lin(shift=np.pi/4, mult=-np.pi/4)
        #                 ),
    )
    # return  {
    # 'rand_drop' : A.GaussianDroplet(
    #                     sigma=A.Signals("t") | A.Sin(hz=1) | A.Lin(shift=np.pi/8, mult=-np.pi/16),
    #                     color=[A.Const(255), A.Signals("vol") | A.Lin(mult=255), A.Signals("pitch") | A.Lin(mult=255)], 
    #                     pos=[A.Rand([-np.pi, np.pi]), A.Rand([0, np.pi])]
    # ),
    # 'pos_drop' : A.GaussianDroplet(
    #                     sigma=A.Signals("t") | A.Sin(hz=0.5) | A.Lin(shift=np.pi/16, mult=-np.pi/16),
    #                     color=[A.Const(1), A.Const(0), A.Const(0)], 
    #                     pos=[A.Const(-np.pi/2), A.Const(np.pi/2)]
    # ),
    # 'uniform_rain' : A.GaussianRain(
    #                     radius=A.Const(np.pi/16),
    #                     color=[A.Signals("vol"), A.Const(0), A.Signals("rand")], 
    #                     nr_droplets=5, 
    #                     drop_duration=A.Const(1)
    # ),
    # 'theta_jiggle' : A.ThetaRing(
    #                     width=A.Const(np.pi/16),
    #                     color=[A.Const(1), A.Const(0), A.Const(1)], 
    #                     pos=A.Const(np.pi/16)#A.Sin(hz=0.5) | A.Lin(shift=np.pi/4, mult=-np.pi/4)
    # )
    # }
