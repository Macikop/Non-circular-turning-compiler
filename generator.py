import math
import decimal

decimal.getcontext().prec = 5

def sgn (i):
    return (i>0)*2 - 1 if i != 0 else 0


first_file =[]

with open("GCODE.nc", "r") as f:
    first_file = f.readlines()

points = []

x = 0
y = 0

for line in first_file:
    words = line.split()
    for word in words:
        if word[0] == "X":
            x = decimal.Decimal(word[1:])
        if word[0] == "Y":
            y = decimal.Decimal(word[1:])
    point = [x, y]
    if point != [0,0]:
        points.append(point)

print(points)

new_points = []

for punkt in points:
    x = punkt[0]
    y = punkt[1]
    r = decimal.Decimal(math.sqrt((x*x) + (y*y)))

    f = decimal.Decimal(r*decimal.Decimal((2*math.pi))/decimal.Decimal((math.acos(x/r))*sgn(y)))
    new_points.append([2*r, f])

print (new_points)

with open("new gcode.nc", "w") as f:
    for n in new_points:
        f.write(f"G32 X{n[0]} F{n[1]}\n")