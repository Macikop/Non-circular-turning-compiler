%
O00001
(Using G0 which travels along dogleg path.)
(T1 D=1.5 CR=0. - ZMIN=-1. - flat end mill)
G90 G17
G21
G53 G0 Z0.

(Trace1)
T1 M6
(Kompozyty, wlokno szklane, PCB)
S5000 M3
G54
G17 G90
G0 X0. Y9.
G43 Z15. H1
G0 Z4.
G1 Z-1. F333.33
X-7.794 Y-4.5 F500.
X7.794
X0. Y9.
Z4.
G0 Z15.

M5
G53 G0 Z0.
X0.
G53 G0 Y0.
M30

%
