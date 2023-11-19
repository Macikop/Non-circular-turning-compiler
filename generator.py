import math
import decimal

arc_tolerance = (0.1)
line_sampling = (0.017) #0.017 - 1 deg

def sgn (i):
    return (i>0)*2 - 1 if i != 0 else 0

def normalize_angle(angle):
    angle = round(angle,5)
    if angle < 0:
        while True:
            angle = angle + 2*math.pi
            if angle >= 0:
                break
        return angle
    elif angle > 2*math.pi:
        while True:
            angle = angle - 2*math.pi
            if angle <= 2*math.pi:
                break
        return angle
    else:
        return angle


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
                    x = (word[1:])
                if word[0] == "Y":
                    y = (word[1:])
            point = [x, y]
        elif words[0] == "G02" or words[0] == "G03":
            current_position = [x,y]
            end_position = [0,0]
            center = [0,0]
            for word in words:
                if word[0] == "X":
                    end_position[0] = (word[1:])
                if word[0] == "Y":
                    end_position[1] = (word[1:])
                if word[0] == "I":
                    center[0] = (word[1:])
                if word[0] == "J":
                    center[1] = (word[1:])

            radius_sq_c = ((current_position[0] - center[0])**2 + (current_position[1] - center[1])**2)
            radius_sq_e = ((end_position[0] - center[0])**2 + (end_position[1] - center[1])**2)
            radius = 0

            if radius_sq_c == radius_sq_e:
                radius = (math.sqrt(radius_sq_c))
            else:
                raise Exception("wrong radius")

            alpha = math.atan(end_position[1]/end_position[0])
            beta = math.atan(current_position[1]/current_position[0])
            angular_travel = (alpha - beta)

            segments = math.floor((math.fabs((0.5)*angular_travel*radius))/(math.sqrt(arc_tolerance*(2*radius*arc_tolerance))))

            theta_per_segment = angular_travel/segments
            point = [0,0]
            for i in range(1,segments):
                x_p = (center[0] + (radius*(math.cos(i*theta_per_segment))))
                y_p = (center[1] + (radius*(math.sin(i*theta_per_segment))))
                point = [x_p, y_p]
                points.append(point)

            points.append([end_position[0],end_position[1]])

        if point != [0,0]:
            points.append(point)

print(points)

new_points = []
for punkt in points:
    x = float(punkt[0])
    y = float(punkt[1])
    r = math.sqrt((x*x) + (y*y))
    phi = normalize_angle(math.acos(x/r)*sgn(y))

    new_points.append([r, phi])

pints = []

for n, p in enumerate(new_points):
    if n > 0:
        starting_angle = new_points[n-1][1]
        ending_angle = new_points[n][1]
        if ending_angle > starting_angle:
            theta = ending_angle - starting_angle
        else:
            theta = ((2*math.pi)-starting_angle)+ending_angle
            
        if theta > math.pi:
            raise Exception("wrong shape, the axis of rotation must be included into the shape")
        #print(angle)
        if theta > line_sampling:
            segments = int(math.floor(math.fabs(theta/line_sampling)))
            #print(segments)
            try:
                radial_line_angle = normalize_angle(math.atan((new_points[n-1][0]*math.cos(new_points[n-1][1]) - new_points[n][0]*math.cos(new_points[n][1]))/(new_points[n][0]*math.sin(new_points[n][1]) - new_points[n-1][0]*math.sin(new_points[n-1][1]))))
            except:
                if new_points[n][0]*math.sin(new_points[n][1])>0:
                    radial_line_angle = math.pi/2
                else:
                    radial_line_angle = math.pi*3/2
                    
            r0 = new_points[n][0] * math.cos(normalize_angle(new_points[n][1]-radial_line_angle))
            
            for i in range(1, segments):
                
                new_phi = normalize_angle(starting_angle + i * line_sampling)
                new_r = r0 * (1/math.cos(new_phi - radial_line_angle))
                pints.append([new_r, new_phi])
        pints.append(p)
    else:
        pints.append(p)
        
#print(new_points)
#print("\n")
#print(pints)

with open("new gcode.nc", "w") as f:
    for n, radial_point in enumerate(pints):
        if n > 0:
            diameter = round(2*radial_point[0],3)
            feedrate = round((math.fabs(radial_point[0]- pints[n-1][0]) * 2 * math.pi)/(normalize_angle(radial_point[1]-pints[n-1][1])),3)
            f.write(f"G32 X{diameter} F{feedrate}\n")
        else:
            diameter = round(2*radial_point[0],3)
            f.write(f"G00 X{diameter}\n")
                           
#with open("new gcode.nc", "w") as f:
#    for n in new_points:
#        f.write(f"G32 X{n[0]} F{n[1]}\n")