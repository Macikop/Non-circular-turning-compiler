import math
import tkinter as tk
from tkinter.filedialog import askopenfile

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

def parse_gcode_form_file(file_name):
    file_content =[]

    with open(file_name, "r") as f:
        file_content = f.readlines()

    points = []

    x = 0
    y = 0

    for line in file_content:
        point =[0,0]
        words = line.split()
        if words != []:
            if words[0] == "G00" or words[0] == "G01":
                for word in words:
                    if word[0] == "X":
                        x = float(word[1:])
                    if word[0] == "Y":
                        y = float(word[1:])
                point = [x, y]
            if point != [0,0]:
                points.append(point)
            elif words[0] == "G02" or words[0] == "G03":
                current_position = [float(x),float(y)]
                end_position = [0,0]
                center = [0,0]
                for word in words:
                    if word[0] == "X":
                        end_position[0] = float(word[1:])
                    if word[0] == "Y":
                        end_position[1] = float(word[1:])
                    if word[0] == "I":
                        center[0] = float(word[1:])
                    if word[0] == "J":
                        center[1] = float(word[1:])
                        
                x = end_position[0]
                y = end_position[1]

                radius_sq_c = ((current_position[0] - center[0])**2 + (current_position[1] - center[1])**2)
                radius_sq_e = ((end_position[0] - center[0])**2 + (end_position[1] - center[1])**2)
                radius = 0
                radius = (math.sqrt(radius_sq_c))
                if radius_sq_c == radius_sq_e:
                    radius = (math.sqrt(radius_sq_c))
                else:
                    raise Exception("wrong radius")
                
                alpha = math.atan2(end_position[1]-center[1],end_position[0]-center[0])
                beta = math.atan2(current_position[1]-center[1],current_position[0]-center[0])
                
                if words[0] == "G03":
                    angular_travel = normalize_angle(alpha - beta)
                else: 
                    angular_travel = normalize_angle(beta - alpha)                

                segments = math.floor((math.fabs((0.5)*angular_travel*radius))/(math.sqrt(arc_tolerance*(2*radius*arc_tolerance))))
                g2_points =[]
                theta_per_segment = angular_travel/segments
                for i in range(1,segments):
                    new_center = [0,0]
                    
                    new_start = [current_position[0] - center[0], current_position[1] - center[1]]
                    new_end = [end_position[0] - center[0], end_position[1] - center[1]]
                    if words[0] == "G03":
                        g2_points =[]
                        new_x = new_start[0]*math.cos(i*theta_per_segment) - new_start[1]*math.sin(i*theta_per_segment)
                        new_y = new_start[0]*math.sin(i*theta_per_segment) + new_start[1]*math.cos(i*theta_per_segment)
                        
                        x_p = new_x + center[0]
                        y_p = new_y + center[1]
                        
                        point = [x_p, y_p]
                        points.append(point)
                    else:
                        new_x = (new_end[0]*math.cos(i*theta_per_segment) - new_end[1]*math.sin(i*theta_per_segment))
                        new_y = (new_end[0]*math.sin(i*theta_per_segment) + new_end[1]*math.cos(i*theta_per_segment))
                        
                        x_p = new_x + center[0]
                        y_p = new_y + center[1]
                        
                        g2_points.append([x_p, y_p])
                        
                    #x_p = new_x + center[0]
                    #y_p = new_y + center[1]
                    #
                    #point = [x_p, y_p]
                    #points.append(point)
                    
                if g2_points != []:
                    for i in range(len(g2_points)):
                        points.append(g2_points[len(g2_points)-i-1])
                points.append([end_position[0],end_position[1]])

            
    return points

def change_to_polar(cartesian_points):
    new_points = []
    for punkt in cartesian_points:
        x = float(punkt[0])
        y = float(punkt[1])
        r = math.sqrt((x*x) + (y*y))
        phi = normalize_angle(math.acos(x/r)*sgn(y))

        new_points.append([r, phi])
    return new_points

def split_lines(polar_points):
    pints = []

    for n, p in enumerate(polar_points):
        if n > 0:
            starting_angle = polar_points[n-1][1]
            ending_angle = polar_points[n][1]
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
                    radial_line_angle = normalize_angle(math.atan((polar_points[n-1][0]*math.cos(polar_points[n-1][1]) - polar_points[n][0]*math.cos(polar_points[n][1]))/(polar_points[n][0]*math.sin(polar_points[n][1]) - polar_points[n-1][0]*math.sin(polar_points[n-1][1]))))
                except:
                    if polar_points[n][0]*math.sin(polar_points[n][1])>0:
                        radial_line_angle = math.pi/2
                    else:
                        radial_line_angle = math.pi*3/2
                        
                r0 = polar_points[n][0] * math.cos(normalize_angle(polar_points[n][1]-radial_line_angle))
                
                for i in range(1, segments):
                    
                    new_phi = normalize_angle(starting_angle + i * line_sampling)
                    new_r = r0 * (1/math.cos(new_phi - radial_line_angle))
                    pints.append([new_r, new_phi])
            pints.append(p)
        else:
            pints.append(p)
    return pints

def output_gcode(polar_splitted_points):
    with open("new gcode.nc", "w") as f:
        f.write("G90 G54 G18 G21; \nT101 M17; \nG99 F0.2; \nG97 M03 S40;\n\n")
        for n, radial_point in enumerate(polar_splitted_points):
            if n > 0:
                diameter = round(2*radial_point[0],3)
                feedrate = round((math.fabs(radial_point[0]- polar_splitted_points[n-1][0]) * 2 * math.pi)/(normalize_angle(radial_point[1]-polar_splitted_points[n-1][1])),3)
                f.write(f"G32 X{diameter} F{feedrate};\n")
            else:
                diameter = round(2*radial_point[0],3)
                f.write(f"G00 X{diameter};\n")
                
        f.write("\nG00 X100;\nG28;\nM05;\nM30;")    

class window():
    filename = ""
    
    def file(self): 
        self.filename = askopenfile()
        
    def compile(self):
        output_gcode(split_lines(change_to_polar(parse_gcode_form_file(self.filename))))
    
    def setup(self):
        window = tk.Tk()
        window.title("Haas non-circular turning compiler")
        icon = tk.PhotoImage(file="icon.png")
        window.iconphoto(True, icon)
        window.geometry("600x600")
        B = tk.Button(window, text = "Load File", command= self.file)
        B.place(x=10, y=10)
        setting_arc = tk.Text(window, height=1, width=10).place(x=100, y=50)
        first_label = tk.Label(window, text="Arc tolerance").place(x=10, y=50)
        setting_line = tk.Text(window, height=1, width=10).place(x=100, y=80)
        second_label = tk.Label(window, text="Line tolerance").place(x=10, y=80)
        
        file = tk.Label(window, text=self.filename,).place(x=50, y=10)   
        ready = tk.Button(window, text="Compile", command= self.compile).place(x=10, y=150)

        window.mainloop()


def main():
    #w = window()
    #w.setup()
    output_gcode(split_lines(change_to_polar(parse_gcode_form_file("arcs_example.nc"))))
    
if __name__ == "__main__":
    main()