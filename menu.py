####This is a custom menu.py script to made for Jessica
####to the Nuke 5 interface.
#### copy and paste the Custom Scripts and Custom Imports section

import sys  
import nuke

#Custom Imports
import writeRead

print 'Loading Dug Menus...'
menubar = nuke.menu("Dug Tools")

# Custom Scripts
n = m.addMenu("Utility")
m.addCommand("Utility/Nodes/writeREAD", "writeRead.writeRead()", "+r", icon="")