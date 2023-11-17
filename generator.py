import math
import decimal

arc_tolerance = decimal.Decimal(0.01)
line_sampling = decimal.Decimal(0.008)


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
    point =[0,0]
    words = line.split()
    if words != []:
        if words[0] == "G00" or words[0] == "G01":
            for word in words:
                if word[0] == "X":
                    x = decimal.Decimal(word[1:])
                if word[0] == "Y":
                    y = decimal.Decimal(word[1:])
            point = [x, y]
        elif words[0] == "G02" or words[0] == "G03":
            current_position = [x,y]
            end_position = [0,0]
            center = [0,0]
            for word in words:
                if word[0] == "X":
                    end_position[0] = decimal.Decimal(word[1:])
                if word[0] == "Y":
                    end_position[1] = decimal.Decimal(word[1:])
                if word[0] == "I":
                    center[0] = decimal.Decimal(word[1:])
                if word[0] == "J":
                    center[1] = decimal.Decimal(word[1:])

            radius_sq_c = decimal.Decimal((current_position[0] - center[0])**2 + (current_position[1] - center[1])**2)
            radius_sq_e = decimal.Decimal((end_position[0] - center[0])**2 + (end_position[1] - center[1])**2)
            radius = 0

            if radius_sq_c == radius_sq_e:
                radius = decimal.Decimal(math.sqrt(radius_sq_c))
            else:
                raise Exception("wrong radius")

            alpha = math.atan(end_position[1]/end_position[0])
            beta = math.atan(current_position[1]/current_position[0])
            angular_travel = decimal.Decimal(alpha - beta)

            segments = math.floor(decimal.Decimal(math.fabs(decimal.Decimal(0.5)*angular_travel*radius))/decimal.Decimal(math.sqrt(arc_tolerance*(2*radius*arc_tolerance))))

            theta_per_segment = angular_travel/segments
            point = [0,0]
            for i in range(1,segments):
                x_p = decimal.Decimal(center[0] + (radius*decimal.Decimal(math.cos(i*theta_per_segment))))
                y_p = decimal.Decimal(center[1] + (radius*decimal.Decimal(math.sin(i*theta_per_segment))))
                point = [x_p, y_p]
                points.append(point)

            points.append([end_position[0],end_position[1]])

        if point != [0,0]:
            points.append(point)

print(points)

new_points = []

for punkt in points:
    x = punkt[0]
    y = punkt[1]
    r = decimal.Decimal(math.sqrt((x*x) + (y*y)))
    phi = decimal.Decimal((math.acos(x/r))*sgn(y))

    new_points.append([r, phi])

print (new_points)

for n, p in enumerate(new_points):
    if n > 1:
        angle = new_points[n][1] - new_points[n-1][1]
        if angle < 0:
            raise Exception("wrong shape")
        
        if angle > line_sampling:
            gamma = new_points[n-1][1]
            delta = new_points[n][1]
            segments = (delta-gamma)/line_sampling
            
            for i in range(1, segments):
                new_r = new_points[n][0] * (1/math.cos(new_points[n][1] + (i*line_sampling))) #if not working chamge sign
                new_phi = gamma + i*line_sampling

                
                           

with open("new gcode.nc", "w") as f:
    for n in new_points:
        f.write(f"G32 X{n[0]} F{n[1]}\n")