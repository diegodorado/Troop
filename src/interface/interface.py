from __future__ import absolute_import, print_function


from ..config import *
from ..message import *
from ..logfile import Log
from ..interpreter import *

from .textbox import ThreadSafeText
from .console import Console
from .peer import Peer, rgb2hex, hex2rgb
from .drag import Dragbar
from .bracket import BracketHandler
from .line_numbers import LineNumbers
from .menu_bar import MenuBar
from .utils import new_operation
from .mouse import Mouse

try:
    from Tkinter import *
    import tkFileDialog
    import tkFont
    from tkColorChooser import askcolor
except ImportError:
    from tkinter import *
    from tkinter import filedialog as tkFileDialog
    from tkinter import font as tkFont
    from tkinter.colorchooser import askcolor

import os, os.path
import time
import sys
import webbrowser

class BasicInterface:
    """ Class for displaying basic text input data.
    """
    def __init__(self):
        self.root=Tk()
        self.root.configure(background=COLOURS["Background"])
        
        self.is_logging = False
        self.logfile = None
        self.wait_msg = None
        self.waiting  = None

        # Store information about the last key pressed
        self.last_keypress  = ""
        self.last_row       = 0
        self.last_col       = 0
        
    def run(self):
        """ Starts the Tkinter loop and exits cleanly if interrupted"""
        # Continually check for messages to be sent
        self.client.update_send()
        self.update_graphs()
        try:
            self.root.mainloop()
        except (KeyboardInterrupt, SystemExit):
            self.kill()
        return
    
    def kill(self):
        """ Terminates cleanly """
        stdout("Quitting")
        self.root.destroy()
        return

    def reset_title(self):
        """ Overloaded in Interface class """
        return

    def colour_line(self, line):
        """ Embold keywords defined in `Interpreter.py` """

        if 1:

            return

        # Get contents of the line

        start, end = "{}.0".format(line), "{}.end".format(line)
        
        string = self.text.get(start, end)

        # Go through the possible tags

        for tag_name, tag_finding_func in self.lang.re.items():

            self.text.tag_remove(tag_name, start, end)
            
            for match_start, match_end in tag_finding_func(string):
                
                tag_start = "{}.{}".format(line, match_start)
                tag_end   = "{}.{}".format(line, match_end)

                self.text.tag_add(tag_name, tag_start, tag_end)
                
        return

class DummyInterface(BasicInterface):
    """ Only implemented in server debug mode """
    def __init__(self):
        BasicInterface.__init__(self)
        self.lang = DummyInterpreter()
        self.text=ThreadSafeText(self, bg=COLOURS["Background"], fg="white", insertbackground=COLOURS["Background"], height=15, bd=0)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.marker = Peer(-1, self.text)
        self.lang.start()

class Interface(BasicInterface):
    def __init__(self, client, title, language, logging=False):

        # Inherit

        BasicInterface.__init__(self)

        self.client = client

        # Set language -- TODO have knowledge of language and set boolean to True

        self.lang = language.start()
        self.interpreters = {name: BooleanVar() for name in langnames}

        # Set logging

        if logging:

            self.set_up_logging()

        # Set title and configure the interface grid

        self.title = title
        
        self.root.title(self.title)

        self.root.columnconfigure(0, weight=0) # Line numbers
        self.root.columnconfigure(1, weight=1) # Text and console

        self.root.rowconfigure(0, weight=1) # Textbox
        self.root.rowconfigure(1, weight=0) # Dragbar
        self.root.rowconfigure(2, weight=0) # Console
        
        self.root.protocol("WM_DELETE_WINDOW", self.kill )

        icon = os.path.join(os.path.dirname(__file__), "img", "icon")

        try:

            # Use .ico file by default
            self.root.iconbitmap(icon + ".ico")
            
        except:

            try:
                # Use .gif if necessary
                self.root.tk.call('wm', 'iconphoto', self.root._w, PhotoImage(file=icon + ".gif"))

            except:

                # If there is no image, just ignore for now -- this is not good practice
                pass

        # Track whether user wants transparent background

        self.transparent = BooleanVar()
        self.transparent.set(False)
        self.using_alpha = (SYSTEM != WINDOWS)

        # Scroll bar
        self.scroll = Scrollbar(self.root)
        self.scroll.grid(row=0, column=3, sticky='nsew')

        # Text box
        self.text=ThreadSafeText(self, bg=COLOURS["Background"], fg="white", insertbackground=COLOURS["Background"], height=15, bd=0)
        self.text.grid(row=0, column=1, sticky="nsew", columnspan=2)
        self.scroll.config(command=self.text.yview)

        # Line numbers
        self.line_numbers = LineNumbers(self.text, width=55, bg=COLOURS["Background"], bd=0, highlightthickness=0)
        self.line_numbers.grid(row=0, column=0, sticky='nsew')
        
        # Drag is a small line that changes the size of the console
        self.drag = Dragbar( self )
        self.drag.grid(row=1, column=0, stick="nsew", columnspan=4)

        # Console Box
        self.console = Console(self.root, bg=COLOURS["Console"], fg="white", height=5, width=10, font="Font")
        self.console.grid(row=2, column=0, columnspan=2, stick="nsew")
        sys.stdout = self.console # routes stdout to print to console

        # Statistics Graphs
        self.graphs = Canvas(self.root, bg=COLOURS["Stats"], width=450, bd=0, highlightthickness=0)
        self.graphs.grid(row=2, column=2, sticky="nsew")
        # self.graph_queue = queue.Queue()

        # Console scroll bar
        self.c_scroll = Scrollbar(self.root)
        self.c_scroll.grid(row=2, column=3, sticky='nsew')
        self.c_scroll.config(command=self.console.yview)

        # Creative constraints - PUT IN OWN CLASS

        from . import constraints
        constraints = vars(constraints)

        self.default_constraint  = "anarchy"
        self.creative_constraints = {name: BooleanVar() for name in constraints if not name.startswith("_")}
        self.creative_constraints[self.default_constraint].set(True)
        self.__constraint__ = constraints[self.default_constraint]()

        # Menubar

        self.menu = MenuBar(self, visible = True)

        # Key bindings
        
        CtrlKey = "Command" if SYSTEM == MAC_OS else "Control"

        self.text.bind("<Key>", self.key_press)

        # Evaluating code

        self.text.bind("<{}-Return>".format(CtrlKey), self.evaluate)
        self.text.bind("<Alt-Return>", self.single_line_evaluate)

        # self.text.bind("<{}-Right>".format(CtrlKey), self.CtrlRight)
        # self.text.bind("<{}-Left>".format(CtrlKey), self.CtrlLeft)
        self.text.bind("<{}-Home>".format(CtrlKey),     self.key_ctrl_home)
        self.text.bind("<{}-End>".format(CtrlKey),      self.key_ctrl_end)
        self.text.bind("<{}-period>".format(CtrlKey),   self.stop_sound)

        self.text.bind("<{}-m>".format(CtrlKey), self.toggle_menu)

        # Key bindings to handle select
        # self.text.bind("<Shift-Left>",  self.SelectLeft)
        # self.text.bind("<Shift-Right>", self.SelectRight)
        # self.text.bind("<Shift-Up>",    self.SelectUp)
        # self.text.bind("<Shift-Down>",  self.SelectDown)
        # self.text.bind("<Shift-End>",   self.SelectEnd)
        # self.text.bind("<Shift-Home>",  self.SelectHome)
        self.text.bind("<{}-a>".format(CtrlKey), lambda e: None)

        # Copy and paste key bindings

        # self.text.bind("<{}-c>".format(CtrlKey), self.Copy)
        # self.text.bind("<{}-x>".format(CtrlKey), self.Cut)
        # self.text.bind("<{}-v>".format(CtrlKey), self.Paste)

        # # Undo -- not implemented
        # self.text.bind("<{}-z>".format(CtrlKey), self.Undo)    
        # self.text.bind("<{}-y>".format(CtrlKey), self.Redo)    

        # Handling mouse events
        self.left_mouse = Mouse(self)
        # self.leftMouse_isDown = False
        # self.leftMouseClickIndex = "0.0"
        self.text.bind("<Button-1>", self.mouse_press_left)
        # self.text.bind("<B1-Motion>", self.leftMouseDrag)
        # self.text.bind("<ButtonRelease-1>", self.leftMouseRelease)
        # self.text.bind("<Button-2>", self.rightMousePress) # disabled
        
        # select_background
        self.text.tag_configure(SEL, background=COLOURS["Background"])   # Temporary fix - set normal highlighting to background colour
        # self.text.bind("<<Selection>>", self.Selection)


        # Disabled Key bindings (for now)

        disable = lambda e: "break"

        for key in list("qwertyuipdfghjklbm") + ["slash"]:

            self.text.bind("<{}-{}>".format(CtrlKey, key), disable)

        # Allowed key-bindings

        self.text.bind("<{}-equal>".format(CtrlKey),  self.increase_font_size)
        self.text.bind("<{}-minus>".format(CtrlKey),  self.decrease_font_size)

        self.text.bind("<{}-s>".format(CtrlKey),  self.menu.save_file)
        self.text.bind("<{}-o>".format(CtrlKey),  self.menu.open_file)
        self.text.bind("<{}-n>".format(CtrlKey),  self.menu.new_file)

        self.ignored_keys = (CtrlKey + "_L", CtrlKey + "_R", "sterling")

        # Directional commands

        self.directions = ("Left", "Right", "Up", "Down", "Home", "End")

        self.handle_direction = {}
        self.handle_direction["Left"]  = self.key_left
        self.handle_direction["Right"] = self.key_right
        self.handle_direction["Down"]  = self.key_down
        self.handle_direction["Up"]    = self.key_up
        self.handle_direction["Home"]  = self.key_home
        self.handle_direction["End"]   = self.key_end

        # Selection indices
        self.sel_start = "0.0"
        self.sel_end   = "0.0"

        # Set the window focus
        self.text.focus_force()

        
        
    def kill(self):
        """ Close socket connections and terminate the application """
        try:

            # if len(self.text.peers) == 1:
            #     from time import sleep
            #     self.client.send(MSG_SET_ALL(self.text.marker.id, self.text.get_contents(), -1))
            #     sleep(0.25)
                
            self.client.recv.kill()
            self.client.send.kill()
            self.lang.kill()
            if self.logfile:
                self.logfile.stop()
            if self.is_logging:
                self.log_file.close()
        except(Exception) as e:
            stdout(e)
        BasicInterface.kill(self)
        return

    def freeze_kill(self, err):
        ''' Displays an error message and stops communicating to the server '''
        self.console.write(err) 
        self.client.send.kill()
        self.client.recv.kill()
        return

    @staticmethod
    def convert(index):
        """ Converts a Tkinter index into a tuple of integers """
        return tuple(int(value) for value in str(index).split("."))

    def init_local_user(self, id_num, name):
        """ Create the peer that is local to the client (text.marker) """

        self.text.marker = self.add_new_user(id_num, name)
        
        return

    def add_new_user(self, user_id, name):
        """ Initialises a new Peer object """

        peer = self.client.peers[user_id] = Peer(user_id, name, self.text) 

        # Create a bar on the graph
        peer.graph = self.graphs.create_rectangle(0,0,0,0, fill=peer.bg)

        # Draw marker

        peer.move(0)

        return peer

    def stop_sound(self, event):
        """ Sends a kill all sound message to the server based on the language """
        self.add_to_send_queue( MSG_EVALUATE_STRING(self.text.marker.id, self.lang.stop_sound() + "\n", reply=1) )
        return "break"

    # def set_insert(self, index):
    #     ''' sets the INSERT and peer mark '''
    #     self.text.mark_set(INSERT, index)
    #     self.text.mark_set(self.text.marker.mark, index)
    #     return

    def reset_title(self):
        """ Resets any changes to the window's title """
        self.root.title(self.title)
        return

    def update_graphs(self):
        """ Continually counts the number of coloured chars and update self.graphs """

        # TODO -- draw graph for peers no longer connected?

        # Only draw graphs once the peer(s) connects

        if len(self.text.peers) == 0:

            self.root.after(100, self.update_graphs)

            return

        # For each connected peer, find the range covered by the tag
        
        for peer in self.text.peers.values():

            tag_name = peer.text_tag

            loc = self.text.tag_ranges(tag_name)

            count = 0

            if len(loc) > 0:

                for i in range(0, len(loc), 2):

                    start, end = loc[i], loc[i+1]

                    start = self.convert(start)
                    end   = self.convert(end)

                    # If the range is on the same line, just count

                    if start[0] == end[0]:

                        count += (end[1] - start[1])

                    else:

                        # Get the first line

                        count += (self.convert(self.text.index("{}.end".format(start[0])))[1] - start[1])

                        # If it spans multiple lines, just count all characters

                        for line in range(start[0] + 1, end[0]):

                            count += self.convert(self.text.index("{}.end".format(line)))[1]

                        # Add the number of the last line

                        count += end[1]

            peer.count = count

        # Once we count all, work out percentages and draw graphs

        total = float(sum([p.count for p in self.text.peers.values()]))

        max_height = self.graphs.winfo_height()
        max_width  = self.graphs.winfo_width()

        # Gaps between edges

        offset_x = 10
        offset_y = 10

        # Graph widths should all fit within the graph box but have maximum width of 40

        graph_w = min(40, (max_width - (2 * offset_x)) / len(self.text.peers))

        for n, peer in enumerate(self.text.peers.values()):

            if peer.graph is not None:

                height = ((peer.count / total) * max_height) if total > 0 else 0

                x1 = (n * graph_w) + offset_x
                y1 = max_height + offset_y
                x2 = x1 + graph_w
                y2 = y1 - (int(height))
                
                self.graphs.coords(peer.graph, (x1, y1, x2, y2))

            # TODO -- Write number / name? Maybe when hovered?
                    
        self.root.update_idletasks()
        self.root.after(100, self.update_graphs)

        return

    def sync_text(self):
        """ Re-sends the information about this client to all connected peers """
        # self.add_to_send_queue(MSG_SYNC(self.text.marker.id, self.text.handle_getall()))
        return

    def add_to_send_queue(self, message, wait=False):
        """ Sends message to server and evaluates them locally if not other markers
            are using the same line. Use the wait flag when you want to force the
            message to go to the server and wait for the response before continuing """

        # Call multiple times if we have a list

        if isinstance(message, list):

            for msg in messages:

                self.add_to_send_queue(msg)

        elif isinstance(message, MESSAGE):
        
            self.client.send_queue.put(message)

        else:

            raise TypeError("Must be MESSAGE or list")
        
        return

    def send_set_mark_msg(self):
        """ Sends a message to server with the location of this peer """
        self.add_to_send_queue(MSG_SET_MARK(self.text.marker.id, self.text.marker.get_index_num(), reply=0))
        return
    
    def key_press(self, event):
        """ 'Pushes' the key-press to the server.
        """

        # Ignore the CtrlKey and non-ascii chars

        if event.keysym in self.ignored_keys:

            return "break"

        elif event.keysym == "F4" and self.last_keypress == "Alt_L":

            self.kill()

            return "break"

        # Get index

        index = self.text.marker.get_index_num() # possibly just use .index_num
        tail  = len(self.text.read()) - index

        operation = []
        index_offset = 0

        # Un-highlight any brackets

        self.text.tag_remove("tag_open_brackets", "1.0", END)

        # If there is a change in the row number, then wait for a reply

        if event.keysym in self.directions:

            return self.handle_direction.get(event.keysym, lambda: None).__call__()

        elif event.keysym == "Delete":

            if tail > 0:
                
                operation = new_operation(index, -1, tail - 1)

        elif event.keysym == "BackSpace":

            if index > 0:

                operation = new_operation(index - 1, -1, tail)

                index_offset = -1

        else:

            if event.keysym == "Return":

                char = "\n"
                
            elif event.keysym == "Tab":
                
                char = " "*4
                
            else:
                
                char = event.char

            if len(char) > 0:

                operation = new_operation(index, char, tail)

                index_offset = len(char)

        if operation:

            # Apply locally

            self.text.apply_local_operation(operation, index_offset)

            # Create message to send

            message = MSG_OPERATION(self.text.marker.id, operation, self.text.revision)

            # Handle the operation on the client side

            self.text.handle_operation(message, client=True)

            # send a set mark message

            self.send_set_mark_msg()

        # Store last key press for Alt+F4 etc

        self.last_keypress  = event.keysym
        
        # Make sure the user sees their cursor

        self.text.see(self.text.marker.mark)
    
        return "break"

    # Directional keypresses

    def key_left(self):
        """ Called when the left arrow key is pressed; decreases the local peer index 
            and updates the location of the label then sends a message to the server
            with the new location """
        self.text.marker.shift(-1)
        self.send_set_mark_msg()
        return "break"


    def key_right(self):
        """ Called when the right arrow key is pressed; increases the local peer index 
            and updates the location of the label then sends a message to the server
            with the new location """
        self.text.marker.shift(1)
        self.send_set_mark_msg()
        return "break"

    def key_down(self):
        """ Called when the down arrow key is pressed; increases the local peer index 
            and updates the location of the label then sends a message to the server
            with the new location """
        tcl_index = self.text.number_index_to_tcl(self.text.marker.get_index_num())
        new_index = self.text.tcl_index_to_number( "{!s}+1lines".format(tcl_index) )

        self.text.marker.move(new_index)
        self.send_set_mark_msg()
        return "break"

    def key_up(self):
        """ Called when the up arrow key is pressed; decrases the local peer index 
            and updates the location of the label then sends a message to the server
            with the new location """
        tcl_index = self.text.number_index_to_tcl(self.text.marker.get_index_num())
        new_index = self.text.tcl_index_to_number( "{!s}-1lines".format(tcl_index) )

        self.text.marker.move(new_index)
        self.send_set_mark_msg()
        return "break"

    def key_home(self):
        """ Called when the home key is pressed; sets the local peer location to 0 
            and updates the location of the label then sends a message to the server
            with the new location """
        row, _ = self.text.number_index_to_row_col(self.text.marker.get_index_num())
        index  = self.text.tcl_index_to_number( "{!r}.0".format(row) )
        
        self.text.marker.move(index)
        self.send_set_mark_msg()
        return "break"

    def key_end(self):
        """ Called when the home key is pressed; sets the local peer location to 0 
            and updates the location of the label then sends a message to the server
            with the new location """
        
        # Convert index to tcl to get row
        row, _ = self.text.number_index_to_row_col(self.text.marker.get_index_num())
        index  = self.text.tcl_index_to_number( "{!r}.end".format(row) )

        self.text.marker.move(index)
        self.send_set_mark_msg()

        return "break"

    def key_ctrl_home(self, event):
        """ Called when the user pressed Ctrl+Home. Sets the local peer index to 0 """
        self.text.marker.move(0)
        self.send_set_mark_msg()
        return "break"

    def key_ctrl_end(self, event):
        self.text.marker.move(len(self.text.read()))
        self.send_set_mark_msg()
        return "break"

    # Selection handling
    # ==================

    def update_select(self, last_row, last_col, new_row, new_col):
        """ Updates the currently selected portion of text for the local peer """
        try:
            start = self.text.index(self.text.marker.sel_tag + ".first")
            end   = self.text.index(self.text.marker.sel_tag + ".last")
            # Whchever (start or end) is equal to last_row/col combo, we update
            old_index = "{}.{}".format(last_row, last_col)
            new_index = "{}.{}".format(new_row, new_col)
            if start == old_index:
                start = new_index
            elif end == "{}.{}".format(last_row, last_col):
                end   = new_index
        except TclError as e:
            start = "{}.{}".format(last_row, last_col)
            end   = "{}.{}".format(new_row, new_col)

        wait_for_reply = (new_row != last_row)

        messages = [ MSG_SELECT(self.text.marker.id, start, end),
                     MSG_SET_MARK(self.text.marker.id, new_row, new_col) ]

        self.add_to_send_queue( messages, wait_for_reply)
                
        return "break"

    def select_left(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = self.Left(row1, col1)
        
        self.update_select(row1, col1, row2, col2)
        
        return "break"

    def select_right(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = self.Right(row1, col1)
        
        self.update_slect(row1, col1, row2, col2)

        return "break"
    
    def select_up(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = self.Up(row1, col1)
        
        self.update_elect(row1, col1, row2, col2)

        return "break"
    
    def select_down(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = self.Down(row1, col1)
        
        self.update_select(row1, col1, row2, col2)
        return "break"

    def select_end(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = (int(i) for i in self.text.index("{}.end".format(row1)).split("."))
        
        self.update_select(row1, col1, row2, col2)

        return "break"

    def select_home(self, event):
        """ Finds the currently selected portion of text of the local peer
            and the row/col to update it to and calls self.UpdateSelect  """
        row1, col1 = self.text.index(self.text.marker.mark).split(".")
        row1, col1 = int(row1), int(col1)
        row2, col2 = (int(i) for i in self.text.index("{}.0".format(row1)).split("."))
        
        self.update_select(row1, col1, row2, col2)

        return "break"

    def select_all(self, event=None):
        """ Tells the server to highlight all the text in the editor and move
            the marker to 1,0 """
        start = "1.0"
        end   = self.text.index(END)

        messages = [ MSG_SELECT(self.text.marker.id, start, end),
                     MSG_SET_MARK(self.text.marker.id, 1, 0) ]

        self.add_to_send_queue( messages, wait=True )
                
        return "break"

    def selection(self, event=None):
        """ Overrides handling of selected areas """
        self.text.tag_remove(SEL, "1.0", END)
        return

    # Evaluating lines
    # ================

    def get_current_block(self):
        """ Finds the 'block' of code that the local peer is currently in
            and returns a tuple of the start and end row """
        return self.lang.get_block_of_code(self.text, self.text.marker.get_tcl_index())


    def single_line_evaluate(self, event=None):
        """ Finds contents of the current line and sends a message to each user (inc. this one) to evaluate """

        row, _ = self.text.number_index_to_row_col(self.text.marker.get_index_num())
        a, b   = "{}.0".format(row), "{}.end".format(row)

        if self.text.get(a, b).lstrip() != "":
            
            self.add_to_send_queue( MSG_EVALUATE_BLOCK(self.text.marker.id, row, row) )
        
        return "break"

    def evaluate(self, event=None):
        """ Finds the current block of code to evaluate and tells the server """
        
        lines = self.get_current_block()
        
        a, b = ("%d.0" % n for n in lines)

        string = self.text.get( a , b ).lstrip()

        if string != "":

            #  Send notification to other peers

            msg = MSG_EVALUATE_BLOCK(self.text.marker.id, lines[0], lines[1])
            
            self.add_to_send_queue( msg )
                
        return "break"

    # Font size
    # =========

    def ChangeFontSize(self, amount):
        """ Updates the font sizes of the text based on `amount` which
            can be positive or negative """
        self.root.grid_propagate(False)
        for font in self.text.font_names:
            font = tkFont.nametofont(font)
            size = max(8, font.actual()["size"] + amount)
            font.configure(size=size)
            self.text.char_w = self.text.font.measure(" ")
            self.text.char_h = self.text.font.metrics("linespace")
        return

    def decrease_font_size(self, event):
        """ Calls `self.ChangeFontSize(-1)` and then resizes the line numbers bar accordingly """
        self.ChangeFontSize(-1)
        self.line_numbers.config(width=self.line_numbers.winfo_width() - 2)
        # self.text.refreshPeerLabels() # -- why this doesn't work?
        return 'break'

    def increase_font_size(self, event=None):
        """ Calls `self.ChangeFontSize(+1)` and then resizes the line numbers bar accordingly """
        self.ChangeFontSize(+1)
        self.line_numbers.config(width=self.line_numbers.winfo_width() + 2)
        # self.text.refreshPeerLabels()
        return 'break'

    # Mouse Clicks
    # ============

    def mouse_press_left(self, event):
        """ Updates the server on where the local peer's marker is when the mouse release event is triggered.
            Selected area is removed un-selected. """

        index = self.left_mouse.click(event)

        self.text.marker.move(index)

        # TODO -- de-select selected text

        message = MSG_SET_MARK(self.text.marker.id, index)

        self.add_to_send_queue( message )

        # Make sure the text box gets focus

        self.text.focus_set()

        return "break"

    # def leftMouseRelease(self, event=None):
    #     """ Updates the server on where the local peer's marker is when the mouse release event is triggered """
        
    #     self.leftMouse_isDown = False

    #     index = self.text.index("@{},{}".format(event.x, event.y))
    #     row, col = index.split(".")
        
    #     self.push_queue_put( MSG_SET_MARK(self.text.marker.id, int(row), int(col)), wait=True )

    #     #self.text.tag_remove(SEL, "1.0", END) # Remove any *actual* selection to stop scrolling

    #     return "break"

    # def leftMouseDrag(self, event):
    #     """ Updates the server with the portion of selected text """
    #     if self.leftMouse_isDown:
    #         sel_start = self.leftMouseClickIndex
    #         sel_end   = self.text.index("@{},{}".format(event.x, event.y))

    #         start, end = self.text.sort_indices([sel_start, sel_end])

    #         self.push_queue_put( MSG_SELECT(self.text.marker.id, start, end), wait=True )
            
    #     return "break"

    def mouse_press_right(self, event):
        """ Disabled """
        return "break"

    # Copy, paste, undo etc
    # =====================

    def undo(self, event):
        ''' Triggers an undo event '''
        self.add_to_send_queue(MSG_UNDO(self.text.marker.id))
        return "break"

    def redo(self, event):
        ''' Override for Ctrl+Y -- Not currently implmented '''
        # self.push_queue_put(MSG_REDO(self.text.marker.id))
        return "break"

    def copy(self, event=None):
        ''' Copies selected text to the clipboard '''
        if self.text.marker.hasSelection():
            text = self.text.get(self.text.marker.sel_start, self.text.marker.sel_end)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        return "break"

    def cut(self, event=None):
        ''' Copies selected text to the clipboard and then deletes it'''
        if self.text.marker.hasSelection():
            text = self.text.get(self.text.marker.sel_start, self.text.marker.sel_end)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            row, col = self.convert(self.text.index(self.text.marker.mark))
            self.add_to_send_queue( MSG_BACKSPACE(self.text.marker.id, row, col), wait=True )
        return "break"
    
    def paste(self, event=None):
        """ Inserts text from the clipboard """
        text = self.root.clipboard_get()
        row, col = self.convert(self.text.index(self.text.marker.mark))
        self.add_to_send_queue( MSG_INSERT(self.text.marker.id, text, row, col), wait=True )
        return "break"

    # Interface toggles
    # =================

    def toggle_menu(self, event=None):
        """ Hides or shows the menu bar """
        self.menu.toggle()
        return "break"

    def ToggleTransparency(self, event=None):
        """ Sets the text and console background to black and then removes all black pixels from the GUI """
        setting_transparent = self.transparent.get()
        if setting_transparent:
            if not self.using_alpha:
                alpha = "#000001" if SYSTEM == WINDOWS else "systemTransparent"
                self.text.config(background=alpha)
                self.line_numbers.config(background=alpha)
                self.console.config(background=alpha)
                self.graphs.config(background=alpha)
                if SYSTEM == WINDOWS:
                    self.root.wm_attributes('-transparentcolor', alpha)
                else:
                    self.root.wm_attributes("-transparent", True)
            else:
                self.root.wm_attributes("-alpha", float(COLOURS["Alpha"]))
        else:
            # Re-use colours
            if not self.using_alpha:
                self.text.config(background=COLOURS["Background"])
                self.line_numbers.config(background=COLOURS["Background"])
                self.console.config(background=COLOURS["Console"])
                self.graphs.config(background=COLOURS["Stats"])
                if SYSTEM == WINDOWS:
                    self.root.wm_attributes('-transparentcolor', "")
                else:
                    self.root.wm_attributes("-transparent", False)
            else:
                self.root.wm_attributes("-alpha", 1)
        return

    # Colour scheme changes
    # =====================

    def edit_colours(self, event=None):
        """ Opens up the colour options dialog """
        from .colour_picker import ColourPicker
        ColourPicker(self)
        return

    def ApplyColours(self, event=None):
        """ Update the IDE for the new colours """ 
        LoadColours() # from config.py
        # Text & Line numbers
        self.text.config(bg=COLOURS["Background"], insertbackground=COLOURS["Background"])
        self.line_numbers.config(bg=COLOURS["Background"])
        # Console
        self.console.config(bg=COLOURS["Console"])
        # Stats
        self.graphs.config(bg=COLOURS["Stats"])
        # Peers
        for peer in self.text.peers.values():
            peer.update_colours()
            peer.configure_tags()
            self.graphs.itemconfig(peer.graph, fill=peer.bg)
        return

    # Misc.
    # =====

    def OpenGitHub(self, event=None):
        """ Opens the Troop GitHub page in the default web browser """
        webbrowser.open("https://github.com/Qirky/Troop")
        return

    def set_interpreter(self, name):
        """ Tells Troop to interpret a new language, takes a string """
        self.lang.kill()

        try:
            self.lang=langtypes[name]()
        
        except ExecutableNotFoundError as e:

            print(e)

            self.lang = DummyInterpreter()

        s = "Changing interpreted lanaguage to {}".format(repr(self.lang))
        print("\n" + "="*len(s))
        print(s)
        print("\n" + "="*len(s))

        self.lang.start()

        return

    # def set_constraint(self, name):
    #     """ Tells Troop to use a new character constraint, see `constraints.py` for more information. """
    #     self.push_queue_put(MSG_CONSTRAINT(self.text.marker.id, name))
    #     return

    # Message logging
    # ===============

    def set_up_logging(self):
        """ Checks if there is a logs folder, if not this creates it """

        log_folder = os.path.join(ROOT_DIR, "logs")

        if not os.path.exists(log_folder):

            os.mkdir(log_folder)

        # Create filename based on date and times
        
        self.fn = time.strftime("client-log-%d%m%y_%H%M%S.txt", time.localtime())
        path    = os.path.join(log_folder, self.fn)
        
        self.log_file   = open(path, "w")
        self.is_logging = True

    def log_message(self, message):
        """ Logs a message to the widget's log_file with a timestamp """
        self.log_file.write("%.4f" % time.time() + " " + repr(str(message)) + "\n")
        return

    def ImportLog(self):
        """ Imports a logfile generated by run-server.py --log and 'recreates' the performance """
        logname = tkFileDialog.askopenfilename()        
        self.logfile = Log(logname)
        self.logfile.set_marker(self.text.marker)
        self.logfile.recreate()
        return

    # Merging font colours - PUT IN OWN CLASS
    # ====================

    def beginFontMerge(self, event=None):
        """ Opens a basic text-entry window and starts the process of "merging fonts".
            This is the slow process of converging all the font colours to the same
            colour. 
        """

        # TODO get values from a window

        _, self.text.merge_colour = askcolor()
        self.text.merge_time = self.ask_duration()

        self.text.merge_recur_time = int( (60000 * self.text.merge_time) / 100)

        self.text.update_font_colours(recur_time = self.text.merge_recur_time )

        return


    def ask_duration(self):
        """ Opens a small window that asks the user to enter a duration """
        popup = popup_window(self.root, title="Set duration")
        
        popup.text.focus_set()

        # Put the popup on top
        
        self.root.wait_window(popup.top)

        return float(popup.value)


class popup_window:
    def __init__(self, master, title=""):
        self.top=Toplevel(master)
        self.top.title(title)
        # Text entry
        lbl = Label(self.top, text="Duration:")
        lbl.grid(row=0, column=0, sticky=W)
        self.text=Entry(self.top)
        self.text.grid(row=0, column=1, sticky=NSEW)
        self.value = None
        # Ok button
        self.button=Button(self.top,text='Ok',command=self.cleanup)
        self.button.grid(row=1, column=0, columnspan=2, sticky=NSEW)
        # Enter shortcut
        self.top.bind("<Return>", self.cleanup)
        # Start
        self.center()

    def cleanup(self, event=None):
        """ Stores the data in the entry fields then closes the window """
        self.value = float(self.text.get())
        self.top.destroy()

    def center(self):
        """ Centers the popup in the middle of the screen """
        self.top.update_idletasks()
        w = self.top.winfo_screenwidth()
        h = self.top.winfo_screenheight()
        size = tuple(int(_) for _ in self.top.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        self.top.geometry("%dx%d+%d+%d" % (size + (x, y)))
        return