import math
import tkinter as tk
import os
import json
import functools
from tkinter.filedialog import askopenfile
from tkinter.simpledialog import askfloat
import tkinter.messagebox as message
from tkinter.filedialog import asksaveasfile
import sys

arc_tolerance = 0.1
line_sampling = 0.017  # 0.017 - 1 deg


def sgn(i):
    return (i > 0) * 2 - 1 if i != 0 else 0


def calculate_phi(x, y):
    angle = 0.0
    if x > 0 and y > 0:
        angle = math.atan(y / x)
    elif x > 0 and y < 0:
        angle = math.atan(y / x) + 2 * math.pi
    elif x < 0:
        angle = math.atan(y / x) + math.pi
    elif x == 0 and y > 0:
        angle = math.pi / 2
    elif x == 0 and y < 0:
        angle = (3 * math.pi) / 2

    return round(angle, 7)


def normalize_angle(angle):
    angle = round(angle, 7)
    if angle < 0:
        while True:
            angle = angle + 2 * math.pi
            if angle >= 0:
                break
        return angle
    elif angle > 2 * math.pi:
        while True:
            angle = angle - 2 * math.pi
            if angle <= 2 * math.pi:
                break
        return angle
    else:
        return angle


def parse_gcode_form_file(file_name):
    file_content = []

    with open(file_name, "r") as f:
        file_content = f.readlines()

    points = []

    g_code_settings = {
        'offset' : 54,
        'coordinate_system' : 1, # 0 - machine, 1 - absolute (G90), 2 - incremental (G91)
        'plane' : 0, #0 - G17, 1 - G18, 2 - G19
        'units_m' : True, # True - mm (G21), False - inch (G20)   
        'tool_number' : 1,
        'spindle_speed' : 20,
        'spindle_state' : 0, #-1 - Left (M04), 0 - Stop (M05), 1 - Right (M03)
        'coolant' : False,
        'program_number' : 'O01000',
        }
    
    active_command = ['', -1, {}]
    ignore = False
    current_command = active_command
    last_i = 0
    splitted_file = []
    
    for i, line in enumerate(file_content):
        line = line.upper()
        current_command = active_command
        line = line.strip()
        if line != '':
            if line[0][0] == 'N':
                line = line[1:]
                
            line = line.split()
            for n, word in enumerate(line):
                word = word.strip('; ')
                command_letter = ''
                command_number = ''
                if not(word in ['', '%']):
                    for char in word:
                        if char == '(':
                            ignore = True
                        if char == ')':
                            ignore = False
                        
                        if ignore == False:
                            if char in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '-']:
                                command_number += char
                            else:
                                if command_letter == '':
                                    command_letter = char
                                else:
                                    raise Exception('Invalid G code command')
                                
                    if command_letter != '' and command_number != '':
                        command_number = float(command_number)
                        if command_letter in ['G', 'M', 'T', 'S', 'O']:
                            current_command = [command_letter, command_number, {}]
                        elif i > last_i:
                            if current_command in ['G', 'M', 'T', 'S']:
                                current_command = [command_letter, command_number, {}]
                            else:
                                current_command = [active_command[0], active_command[1], {command_letter : command_number}]
                        else:
                            if current_command != ['', -1, {}]:
                                current_command[2].update({command_letter : command_number})
                            else:
                                current_command = [command_letter, command_number, {}]
                                
                        if active_command == ['', -1, {}] or active_command != current_command:
                            if current_command[0] == 'G':
                                if current_command[1] in [0, 1, 2, 3]:
                                    active_command = [current_command[0], current_command[1], {}]
                                    
                    if command_letter != '' and command_number != '':
                        if i == 1 and last_i == 0:
                            splitted_file.append(current_command) 
                        
                        if current_command != ['', -1, {}] and splitted_file[-1] != current_command: 
                            splitted_file.append(current_command) 
                        last_i = i
                        
    for n in splitted_file:
        print(n)
    
    starting_point = [0.0,0.0]
    points = []
    cutting_started = False
    

    for command in splitted_file:
        if command[0] == 'G' and command[1] == 0.0 and cutting_started == False:
            arguments = command[2].keys()
            if 'X' in arguments:
                starting_point[0] = command[2]['X']
            if 'Y' in arguments:
                starting_point[1] = command[2]['Y']
                
        elif command[0] == 'G' and command[1] == 1.0:
            if points == [] and starting_point != [0.0, 0.0]:
                points.append(starting_point)
            
            cutting_started = True
            point = [points[-1][0], points[-1][1]]
            arguments = command[2].keys()
            if 'X' in arguments:
                point[0] = command[2]['X']
            if 'Y' in arguments:
                point[1] = command[2]['Y']
            if 'X' in arguments or 'Y' in arguments:
                points.append(point)
                
        elif command[0] == 'G' and (command[1] in [2.0, 3.0]):
            if points == [] and starting_point != [0.0, 0.0]:
                points.append(starting_point)

            cutting_started = True
            
            current_position = [points[-1][0], points[-1][1]]
            end_position = [points[-1][0], points[-1][1]]
            center = [0.0, 0.0]
            
            arguments = command[2].keys()
            if 'X' in arguments:
                end_position[0] = command[2]['X']
            
            if 'Y' in arguments:
                end_position[1] = command[2]['Y']
            
            if 'I' in arguments:
                center[0] = command[2]['I']
            else:
                raise Exception("Missing arguments")
            
            if 'J' in arguments:
                center[1] = command[2]['J']
            else:
                raise Exception("Missing arguments")

            radius_sq_c = (current_position[0] - center[0]) ** 2 + (
                current_position[1] - center[1]
            ) ** 2
            radius_sq_e = (end_position[0] - center[0]) ** 2 + (
                end_position[1] - center[1]
            ) ** 2
            
            if radius_sq_c == radius_sq_e:
                radius = math.sqrt(radius_sq_c)
            else:
                raise Exception("wrong radius")

            alpha = math.atan2(
                end_position[1] - center[1], end_position[0] - center[0]
            )
            beta = math.atan2(
                current_position[1] - center[1], current_position[0] - center[0]
            )

            if command[1] == 3.0:
                angular_travel = normalize_angle(alpha - beta)
            else:
                angular_travel = normalize_angle(beta - alpha)

            segments = math.floor(
                (math.fabs((0.5) * angular_travel * radius))
                / (math.sqrt(arc_tolerance * (2 * radius * arc_tolerance)))
            )
            g2_points = []
            theta_per_segment = angular_travel / segments
            for i in range(1, segments):
                new_center = [0, 0]

                new_start = [
                    current_position[0] - center[0],
                    current_position[1] - center[1],
                ]
                new_end = [end_position[0] - center[0], end_position[1] - center[1]]
                if command[1] == 3.0:
                    g2_points = []
                    new_x = new_start[0] * math.cos(
                        i * theta_per_segment
                    ) - new_start[1] * math.sin(i * theta_per_segment)
                    new_y = new_start[0] * math.sin(
                        i * theta_per_segment
                    ) + new_start[1] * math.cos(i * theta_per_segment)

                    x_p = new_x + center[0]
                    y_p = new_y + center[1]

                    point = [x_p, y_p]
                    points.append(point)
                else:
                    new_x = new_end[0] * math.cos(i * theta_per_segment) - new_end[
                        1
                    ] * math.sin(i * theta_per_segment)
                    new_y = new_end[0] * math.sin(i * theta_per_segment) + new_end[
                        1
                    ] * math.cos(i * theta_per_segment)

                    x_p = new_x + center[0]
                    y_p = new_y + center[1]

                    g2_points.append([x_p, y_p])

            if g2_points != []:
                for i in range(len(g2_points)):
                    points.append(g2_points[len(g2_points) - i - 1])
            points.append([end_position[0], end_position[1]])
    
    return points


def change_to_polar(cartesian_points):
    new_points = []
    for punkt in cartesian_points:
        x = float(punkt[0])
        y = float(punkt[1])
        r = math.sqrt((x * x) + (y * y))
        # phi = normalize_angle(math.acos(x / r) * sgn(y))
        phi = calculate_phi(x, y)

        new_points.append([r, phi])
    return new_points


def split_lines(polar_points):
    pints = []

    for n, p in enumerate(polar_points):
        if n > 0:
            starting_angle = polar_points[n - 1][1]
            ending_angle = polar_points[n][1]
            if ending_angle > starting_angle:
                theta = ending_angle - starting_angle
            else:
                theta = normalize_angle(ending_angle - starting_angle)
            if theta > math.pi:
                raise Exception(
                    "wrong shape, the axis of rotation must be included into the shape"
                )
            # print(angle)
            if theta > line_sampling:
                segments = int(math.floor(math.fabs(theta / line_sampling)))
                # print(segments)
                try:
                    radial_line_angle = normalize_angle(
                        math.atan(
                            (
                                polar_points[n - 1][0]
                                * math.cos(polar_points[n - 1][1])
                                - polar_points[n][0] * math.cos(polar_points[n][1])
                            )
                            / (
                                polar_points[n][0] * math.sin(polar_points[n][1])
                                - polar_points[n - 1][0]
                                * math.sin(polar_points[n - 1][1])
                            )
                        )
                    )
                except:
                    if polar_points[n][0] * math.sin(polar_points[n][1]) > 0:
                        radial_line_angle = math.pi / 2
                    else:
                        radial_line_angle = math.pi * 3 / 2

                r0 = polar_points[n][0] * math.cos(
                    normalize_angle(polar_points[n][1] - radial_line_angle)
                )

                for i in range(1, segments):
                    new_phi = normalize_angle(starting_angle + i * line_sampling)
                    new_r = r0 * (1 / math.cos(new_phi - radial_line_angle))
                    pints.append([new_r, new_phi])
            pints.append(p)
        else:
            pints.append(p)
    return pints


def output_gcode(polar_splitted_points, passes, pitch, Zstart, outside_diameter, file):
    output_string = ""
    depth = Zstart - pitch
    output_string += f"\n"
    output_string += f"G90 G54 G18 G21;\nT101 M17;\nG99 F0.2;\nG00 X{outside_diameter} Z{Zstart};\nG97 M03 S40;\n\n"
    # if use_variables:
    feedrate = 0
    for i in range(passes):
        for n, radial_point in enumerate(polar_splitted_points):
            if n == 0 and i == 0:
                diameter = round(2 * radial_point[0], 3)
                output_string += f"G00 X{diameter} Z{depth};\n"
            elif (
                (n == 0 and i > 0)
                or n == len(polar_splitted_points) - 1
                and i == passes - 1
            ):
                diameter = round(2 * radial_point[0], 3)
                feedrate = round(
                    (
                        math.fabs(radial_point[0] - polar_splitted_points[n - 2][0])
                        * 2
                        * math.pi
                    )
                    / (
                        normalize_angle(
                            radial_point[1] - polar_splitted_points[n - 2][1]
                        )
                    ),
                    3,
                )
                output_string += f"G32 X{diameter} F{feedrate};\n"
            elif n == len(polar_splitted_points) - 1 and i < passes + 1:
                diameter = round(2 * radial_point[0], 3)
                depth = round(depth - pitch, 3)
                feedrate = round(
                    (
                        math.fabs(radial_point[0] - polar_splitted_points[n - 2][0])
                        * 2
                        * math.pi
                    )
                    / (
                        normalize_angle(
                            radial_point[1] - polar_splitted_points[n - 1][1]
                        )
                    ),
                    3,
                )
                output_string += f"G32 X{diameter} F{feedrate};\n"
                output_string += f"G00 X{outside_diameter};\nM05;\nG00 Z{depth};\nM17;\nM03 S40;\n"
            else:
                diameter = round(2 * radial_point[0], 3)
                s = math.fabs(radial_point[0] - polar_splitted_points[n - 1][0])
                feedrate = round(
                    (
                        math.fabs(radial_point[0] - polar_splitted_points[n - 1][0])
                        * 2
                        * math.pi
                    )
                    / (
                        normalize_angle(
                            radial_point[1] - polar_splitted_points[n - 1][1]
                        )
                    ),
                    3,
                )
                output_string += f"G32 X{diameter} F{feedrate};\n"
    # else:
    #    first_line = False
    #    for n, radial_point in enumerate(polar_splitted_points):
    #        if n == 0 and first_line == False:
    #            diameter = round(2*radial_point[0],3)
    #            output_string +=("#501=0")
    #            output_string +=(f"G00 X{diameter} Z{depth};\n")
    #            first_line = True
    #            output_string +=("N10")
    #        elif n == len(polar_splitted_points)-1:
    #            diameter = round(2*radial_point[0],3)
    #            depth = round(depth-pitch, 3)
    #            feedrate = round((math.fabs(math.sqrt((radial_point[0]- polar_splitted_points[n-1][0])**2 + pitch**2)) * 2 * math.pi)/(normalize_angle(radial_point[1]-polar_splitted_points[n-1][1])),3)
    #            output_string +=(f"G32 X{diameter} Z{depth} F{feedrate};\n")
    #        elif n == len(polar_splitted_points) :
    #            diameter = round(2*radial_point[0],3)
    #            feedrate = round((math.fabs(radial_point[0]- polar_splitted_points[n-2][0]) * 2 * math.pi)/(normalize_angle(radial_point[1]-polar_splitted_points[n-2][1])),3)
    #            output_string +=(f"G32 X{diameter} F{feedrate};\n")
    #            output_string +=(f"#501=#501 + {depth}")
    #            output_string +=("GOTO10")
    #        else:
    #            diameter = round(2*radial_point[0],3)
    #            s = math.fabs(radial_point[0]- polar_splitted_points[n-1][0])
    #            feedrate = round((math.fabs(radial_point[0]- polar_splitted_points[n-1][0]) * 2 * math.pi)/(normalize_angle(radial_point[1]-polar_splitted_points[n-1][1])),3)
    #            output_string +=(f"G32 X{diameter} F{feedrate};\n")
    #
    output_string += f"G00 X{outside_diameter};\nG28 U0;\nG28 W0;\nM05;\nM30;\n%"

    file.write(output_string)
    file.close()


class Window:
    filename = ""
    settings = {"setting_arc": 0.0, "setting_line": 0.0}
    pitch = 0
    passes = 1

    def file_destination(self):
        return asksaveasfile(
            initialfile="Untitled.nc",
            defaultextension=".nc",
            filetypes=[("NC file", "*.nc"), ("G-Code files", "*.gcode")],
        )

    def file(self):
        try:
            self.filename = askopenfile(
                filetypes=[("NC file", "*.nc"), ("G-Code files", "*.gcode")]
            )
            self.filelabel.config(text=self.filename.name)
            self.input_file.delete("1.0", "end")
            self.input_file.insert(tk.END, self.filename.read())
        except:
            message.showerror("No file", "No file selected")

    def settings_load(self):
        try:
            with open("settings.json", mode="r") as f:
                content = f.read()
                self.settings = json.loads(content)

            global arc_tolerance
            global line_sampling
            arc_tolerance = self.settings["setting_arc"]
            line_sampling = (self.settings["setting_line"] * math.pi) / 180

        except:
            message.showerror("No file", "Cannot find settings.json")

    def settings_save(self):
        if os.path.exists("settings.json"):
            os.remove("settings.json")
        with open("settings.json", mode="w") as f:
            f.write(json.dumps(self.settings))

    def change_setting(self, setting, message, unit):
        self.settings_load()
        self.settings[setting] = askfloat(
            f"Set {message}", f"Change {message} [{unit}]"
        )
        self.settings_save()

    def compile(self):
        try:
            self.settings_load()
            passes = int(self.passes.get())
            pitch = float(self.pitch.get())
            starting_point = float(self.startingZ.get())
            stock_diameter = float(self.returnX.get())
        except:
            message.showerror("Wrong input", "Program parameters are missing")
            return False

        if (
            self.settings["setting_arc"] > 0.0
            and self.settings["setting_line"] > 0
            and passes > 0
            and pitch > 0
        ):
            try:
                output_gcode(
                    split_lines(
                        change_to_polar(parse_gcode_form_file(self.filename.name))
                    ),
                    passes,
                    pitch,
                    starting_point,
                    stock_diameter,
                    self.file_destination() or open("new_gcode.nc", "w"),
                )
                message.showinfo("Compiling complete", "Compiling complete")
                return True
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                message.showerror(message=str(e) + str(fname) + str(exc_tb.tb_lineno))
                return False
        else:
            message.showerror("Wrong settings", "Wrong settings")
            return False

    def setup(self):
        window = tk.Tk()
        window.title("Haas non-circular turning compiler")
        icon = tk.PhotoImage(file="icon.png")
        window.iconphoto(False, icon)
        window.geometry("800x600")

        menubar = tk.Menu(window, tearoff=0)
        window.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)

        file_menu.add_command(label="Open...", command=self.file)
        file_menu.add_command(label="Close", command=window.destroy)

        settings_menu = tk.Menu(window, tearoff=0)

        settings_menu.add_cascade(
            label="Arc tolerance",
            command=functools.partial(
                self.change_setting, "setting_arc", "Arc Tolerance", "mm"
            ),
        )
        settings_menu.add_cascade(
            label="Line tolerance",
            command=functools.partial(
                self.change_setting, "setting_line", "Line Sampling", "deg"
            ),
        )

        help_menu = tk.Menu(window, tearoff=0)
        help_menu.add_command(label="Instructions")
        help_menu.add_command(label="About")

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        menubar.add_cascade(label="Help", menu=help_menu)

        B = tk.Button(window, text="Load File", command=self.file).place(x=10, y=10)
        tk.Label(window, text="Pitch [mm]").place(x=10, y=50)
        self.pitch = tk.Entry(window)
        self.pitch.place(x=100, y=50)
        tk.Label(window, text="Passes").place(x=10, y=80)
        self.passes = tk.Entry(window)
        self.passes.place(x=100, y=80)

        tk.Label(window, text="Z start [mm]").place(x=10, y=120)
        self.startingZ = tk.Entry(window)
        self.startingZ.place(x=100, y=120)

        tk.Label(window, text="Return X [mm]").place(x=10, y=150)
        self.returnX = tk.Entry(window)
        self.returnX.place(x=100, y=150)

        # self.haas_variables = tk.Checkbutton(window, text='Use haas variables')
        # self.haas_variables.place(x=10, y=120)

        self.input_file = tk.Text(window, height=30, width=25)
        self.filelabel = tk.Label(window)
        self.filelabel.place(x=80, y=10)
        ready = tk.Button(window, text="Compile", command=self.compile).place(
            x=10, y=200
        )

        self.input_file.place(x=250, y=50)

        window.mainloop()


def main():
    w = Window()
    w.setup()
    output_gcode(split_lines(change_to_polar(parse_gcode_form_file("arcs_example.nc"))), 10 , 0.1)

if __name__ == "__main__":
    main()
