class Mouse:
    def __init__(self, widget):
        self.root = widget
        self.is_pressed = False
        self.index = 0
        self.tcl_index = "1.0"

    def click(self, event):
        """ Monitors location and press info about last mouse click based on tcl event"""
        self.is_pressed  = True
        self.tcl_index = self.root.text.index("@{},{}".format( event.x, event.y ))
        self.index = self.root.text.tcl_index_to_number(self.tcl_index)
        return self.index

    def get_index(self):
        """ Returns the index (single number) """
        return self.index