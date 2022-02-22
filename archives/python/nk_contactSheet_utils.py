# -------------------------------------------------------------------------- #
# ---------------------------------------------------------------- HEADER -- #
"""
@copyright: Copyright (C) 2016 ReelFx Creative Studios. All rights reserved.

@organization: ReelFX Creative Studios

@description: Utilities for working with the Insight API

@author: Garrett Moring / Ed Whetstone

@applications: Any

"""

# -------------------------------------------------------------------------- #
# --------------------------------------------------------------- IMPORTS -- #

import nuke
import nukescripts
import ipyapi
import getpass
import webbrowser
import os
from pipe_core.model.pipe_obj import Project

proj = Project.current()


# #####################################################################

dependency_nodes = []
dependent_nodes = []


# #####################################################################

def getDependents(node):
    ignoreThese = ["ContactSheet", "Viewer"]
    for n in node.dependent():
        if n.Class() not in ignoreThese:
            global dependent_nodes
            dependent_nodes.append(n)
            getDependents(n)


# #####################################################################

def getDependencies(node):
    for n in node.dependencies():
        global dependency_nodes
        dependency_nodes.append(n)
        getDependencies(n)


# #####################################################################

def getSeqShotFromRead(node):
    # Return the seq_shot associated with given Read node
    if node.Class() == 'Read':
        readfile = node['file'].value()
        try:
            seq = readfile.split("/")[4]
            shot = readfile.split("/")[5]
            this_shot = '%s-%s' % (seq, shot)

            return this_shot
        except:
            pass

    else:
        return None


# #####################################################################

def getReadsWithinBackdrop(node):
    # Return list of read nodes that are contained by given BackdropNode
    contained_reads = []
    if node.Class() == 'BackdropNode':
        artist = node['label'].value()
        # get position, width, & height
        x_min = node.xpos()
        x_max = x_min + node['bdwidth'].value()
        y_min = node.ypos()
        y_max = y_min + node['bdheight'].value()

        # Check for reads that fit inside the bounds
        for read in nuke.allNodes('Read'):
            if read.xpos() > x_min and read.xpos() < x_max and read.ypos() > y_min and read.ypos() < y_max:
                contained_reads.append(read)

    return contained_reads


# #####################################################################

def listShotsInBackdrop():
    print '\nlistShotsInBackdrop()'

    report = '\nCasting based on BackdropNodes:\n\n'

    for bd_node in nuke.selectedNodes('BackdropNode'):
        report = report + "\n\n" + bd_node['label'].value() + "\n\n"
        shot_list = []
        for read in getReadsWithinBackdrop(bd_node):
            shot_list.append(getSeqShotFromRead(read))

        # Modify report
        for shot in sorted(shot_list):
            report = report + shot + "\n"

        report = report + "-----------------------"


    # Show results!
    p = nuke.Panel('Casting')
    p.setWidth(300)
    p.addNotepad('',report)
    p.show()

    print 'Done\n'


def checkForRenders():

    print '\ncheckForRenders()'

    proj = Project.current()
    projName = proj.name
    unrenderedShots = []

    # Get reads list from selection
    read_list = nuke.selectedNodes('Read')
    if len(read_list) == 0:
        nuke.message('\nNo \'Reads\' selected!\n')

    else:
        # get seq/shot from selected reads
        for read in read_list:
            seq = read['file'].value().split("/")[4]
            shot = read['file'].value().split("/")[5]
            thisShot = "%s_%s" % (seq, shot)
            imageDir = "/render/%s/sequences/%s/%s/lit/master/" % (projName, seq, shot)

            # check if directory exists
            if os.path.isdir(imageDir):
                # Get list of render passes
                renderPasses = os.listdir(imageDir)
                if len(renderPasses) == 0:
                    unrenderedShots.append(thisShot)
                else:
                    read.setSelected(0)

            else:
                print "\n No image directory for %s:\n%s\n" % (thisShot, imageDir)
                unrenderedShots.append(thisShot)

        results = "\n%d shots with no renders:\n\n" % len(unrenderedShots)
        sortedUnRendered = sorted(unrenderedShots)

        for shot in sortedUnRendered:
            results = results + " - " + shot + "\n"

        for node in nuke.allNodes():
            if node.Class() != "Read":
                node.setSelected(0)

        # Show results
        nuke.message(results)
    print 'Done\n'


# #####################################################################

def resetColoredReads():
    # Return Read node colors back to user prefs
    print '\nresetColoredReads()'

    for read in nuke.allNodes('Read'):
        defCol = nuke.defaultNodeColor(read.Class())
        read['tile_color'].setValue(defCol)

    print 'Done\n'


# #####################################################################

def updateSelectedReads():
    print '\nupdateSelectedReads()'
    '''
    Get the latest rendered comp images for selected reads
    '''
    proj = Project.current()
    projName = proj.name
    updatedShots = []

    # get seq shot
    for read in nuke.selectedNodes('Read'):

        if getSeqShotFromRead(read):

            this_shot = getSeqShotFromRead(read)
            seq = this_shot.split("-")[0]
            shot = this_shot.split("-")[1]
            compPath = '/render/%s/sequences/%s/%s/comp/master/shot/live' % (projName, seq, shot)

            print '\nseq: %s\nshot: %s\ncompPath: %s\n' % (seq, shot, compPath)

            # check if this is already a comp read
            if "comp" not in read['file'].value():

                # check if path exists
                if os.path.exists(compPath):
                    # Get full path of file(s)
                    compFiles = os.listdir(compPath)
                    lastFile = compFiles[0]
                    fileVersion = lastFile.split(".")[0].split("_")[-1]
                    newPath = "%s/%s_%s_master_%s.%%v.%%04d.exr" % (compPath, seq, shot, fileVersion)
                    updatedShots.append("%s_%s" % (seq, shot))
                    read['file'].setValue(newPath)

                    # color the node
                    read['tile_color'].setValue(1036794111)

            else:

                # Get full path of file(s)
                try:
                    currentVersion = read['file'].value().rsplit("/",1)[1].split("_")[3].split(".")[0]
                except:
                    currentVersion = '000'

                compFiles = os.listdir(compPath)
                lastFile = compFiles[0]
                liveFile = lastFile.split(".")[0]
                currentFile = read['file'].value().rsplit("/",1)[1].split(".")[0]

                #print '\nlive: %s\ncurrent: %s\n' % (liveFile, currentFile)

                if liveFile != currentFile:
                    newPath = "%s/%s.%%v.%%04d.exr" % (compPath, liveFile)
                    updatedShots.append("%s_%s" % (seq, shot))
                    read['file'].setValue(newPath)

                    # color the node
                    read['tile_color'].setValue(65535)


    message = "%d Reads updated\n\n" % len(updatedShots)

    if len(updatedShots) > 0:
        multipleReads = []

        # sort the list
        sortedShots = sorted(updatedShots)

        for shot in sortedShots:
            # check if it's been counted already
            if shot not in multipleReads:
                # count occurances of this shot
                if sortedShots.count(shot) > 1:

                    multipleReads.append(shot)
                    message = message + shot + " (x%d)\n" % sortedShots.count(shot)

                else:
                    message = message + shot + "\n"

    print "Done\n"
    nuke.message(message)



# #####################################################################

def selAllReads():
    print '\nselAllReads()'

    for node in nuke.allNodes():
        if node.Class() == 'Read':
            node.setSelected(True)
        else:
            node.setSelected(False)

    print 'Done\n'


# #####################################################################

def SideBySide():

    nodes = nuke.selectedNodes()
    amount = len( nodes )
    if amount == 0:

        for node in nuke.allNodes('rfxHUD'):

            if node['side_by_side'].value() == 0:
                node['side_by_side'].setValue(1)
            else:
                node['side_by_side'].setValue(0)

        print 'Done All Nodes\n'

    else:

        for node in nuke.selectedNodes('rfxHUD'):
            if node['side_by_side'].value() == 0:
                node['side_by_side'].setValue(1)
            else:
                node['side_by_side'].setValue(0)

        print 'Done Selected Nodes\n'


# #####################################################################

def FirstLastSwap():

    for node in nuke.selectedNodes('rfxHUD'):
        if node['first_last'].value() == 0:
            node['first_last'].setValue(1)
        else:
            node['first_last'].setValue(0)

    print 'Done\n'

# #####################################################################

def InsightColorBorder():

    for node in nuke.selectedNodes('rfxHUD'):
        if node['insight_color'].value() == 0:
            node['insight_color'].setValue(1)
        else:
            node['insight_color'].setValue(0)

    print 'Done\n'

# #####################################################################

def WarningBorder():

    for node in nuke.selectedNodes('rfxHUD'):
        if node['warning_border'].value() == 0:
            node['warning_border'].setValue(1)
        else:
            node['warning_border'].setValue(0)

    print 'Done\n'

# #####################################################################

def hud_reset():

    for node in nuke.allNodes('rfxHUD'):
        node['side_by_side'].setValue(0)
        node['first_last'].setValue(0)
        node['insight_color'].setValue(0)
        node['warning_border'].setValue(0)

    print 'Done\n'


# #####################################################################

def hookupContactSheet():
    import operator

    # hookup nodes to a contactSheet in order from Left to Right
    print '\nhookupContactSheet()'

    ignoredNodes = ['BackdropNode', 'Write', 'ContactSheet']
    connect_list = []
    error_flag = 0
    message = ''

    for node in nuke.selectedNodes():
        if node.Class() == 'ContactSheet':
            cs_node = node

        elif node.Class() not in ignoredNodes:
            connect_list.append(node)

    try:
        if cs_node:
            pass
    except:
        error_flag = 1
        message = '\nNo Contact Sheet selected!\n'

    if len(connect_list) == 0:
        error_flag = 1
        message = '\nNothing to connect!\n'

    if error_flag == 1:
        nuke.message(message)

    else:
        # Store node positions in dictionary
        connect_dict = {}
        for node in connect_list:
            this_x = node.xpos()
            connect_dict[node] = this_x

        sortedList = sorted([(value,key) for (key,value) in connect_dict.items()])

        # unhook the contactSheet node
        for i in range(0,cs_node.inputs()):
            cs_node.setInput(i,None)

        sorted_x = sorted(connect_dict.items(), key=operator.itemgetter(1))

        # rehook the contactSheet node
        for i, thing in enumerate(sorted_x):
            cs_node.setInput(i,thing[0])


    print 'Done\n'



# #####################################################################

def customCopyRead(read, artist):

    # Record specific parameters & restore them in a new read
    readFile = read['file'].value()
    first = read['first'].value()
    last = read['last'].value()
    frame = read['frame'].value()
    on_error = read['on_error'].value()
    label = read['label'].value()
    lighter = read['lighter'].value()

    # Create new read and copy values into it
    newRead = nuke.createNode('Read', inpanel=False)
    newRead['file'].setValue(readFile)
    newRead['first'].setValue(first)
    newRead['last'].setValue(last)
    newRead['frame'].setValue(frame)
    newRead['on_error'].setValue(on_error)

    # Add custom attribute
    lighter_knob = nuke.EvalString_Knob('lighter', 'Lighter:', artist)
    newRead.addKnob(lighter_knob)
    newRead['label'].setValue(label)
    newRead['lighter'].setValue(lighter)

    return newRead


# #####################################################################

def groupByArtist():
    '''
    For each shot selected (Read nodes) duplicate them
    and sort them into backDrop nodes based on artist.
    Selected reads must have a recorded artist from
    previously running the updateArtist() function.
    '''
    print '\ngroupByArtist()'
    unique_artists = []

    # Get selected shots
    allNodes = nuke.allNodes()
    selected = nuke.selectedNodes('Read')

    # Deselect all
    for node in nuke.allNodes():
        node.setSelected(False)

    # Set global X_max & Y_min
    x_max = -4000
    y_min = 4000

    for node in allNodes:

        if node.Class() == 'BackdropNode':
            bd_x_max = node['bdwidth'].value() + node['xpos'].value()
            bd_y_min = node['ypos'].value()
            if bd_x_max > x_max:
                x_max = bd_x_max
            if bd_y_min < y_min:
                y_min = bd_y_min

        else:
            node_x_max = node.screenWidth() + node['xpos'].value()
            node_y_min = node['ypos'].value()
            if node_x_max > x_max:
                x_max = node_x_max
            if node_y_min < y_min:
                y_min = node_y_min

    x_max += 500
    y_offset = 400

    for read in selected:
        # Check for assigned artist
        if read.knob('lighter'):
            lighter = str(read['lighter'].value())
            if lighter not in unique_artists:
                unique_artists.append(lighter)

    sorted_artists = sorted(unique_artists)

    for count, artist in enumerate(sorted_artists):
        # Collect all reads from selection assigned to this artist
        # and place them in a backdrop node
        this_y = y_min + (y_offset * count)
        this_x = x_max
        artist_reads = []

        for read in selected:
            if read.knob('lighter'):
                if str(read['lighter'].value()) == artist:
                    # Copy the node
                    copyRead = customCopyRead(read, artist)
                    copyRead['xpos'].setValue(this_x)
                    copyRead['ypos'].setValue(this_y)
                    copyRead.setSelected(False)
                    copyRead.setSelected(True)
                    colorReadStatus()
                    copyRead.setSelected(False)
                    artist_reads.append(copyRead)
                    this_x += 120

        # Wrap these nodes in a BackdropNode
        # Get the min/max (x,y) coords of selected nodes
        x_min_bd, x_max_bd, y_min_bd, y_max_bd = get_min_max(artist_reads)
        offset = 60
        font_diff = 50

        bd_x = x_min_bd - offset
        bd_y = y_min_bd - offset - font_diff
        bd_w = x_max_bd - x_min_bd + (offset * 2)
        bd_h = y_max_bd - y_min_bd + (offset * 3) + font_diff

        # Create new Backdrop node
        artist_bd = nuke.createNode('BackdropNode', inpanel = False)
        artist_bd['xpos'].setValue(bd_x)
        artist_bd['ypos'].setValue(bd_y)
        artist_bd['bdwidth'].setValue(bd_w)
        artist_bd['bdheight'].setValue(bd_h)
        artist_bd['note_font_size'].setValue(40)
        artist_bd['label'].setValue(artist)
        artist_bd['tile_color'].setValue(1280068863)
        artist_bd['selected'].setValue(False)

        # Now sort them ascending
        for node in artist_reads:
            node.setSelected(True)

        sortByShot()

    print 'Done\n'


# #####################################################################

def get_min_max(node_list):

    '''
    Returns the minimum & maximum
    x,y coords of nodes in the node_list
    '''
    first_node = node_list[0]

    x_min = first_node['xpos'].value()
    x_max = first_node['xpos'].value() + first_node.screenWidth()

    y_min = first_node['ypos'].value()
    y_max = first_node['ypos'].value() + first_node.screenHeight()

    # Find min/max
    for node in node_list:
        if node['xpos'].value() + node.screenWidth() > x_max:
            x_max = node['xpos'].value() + node.screenWidth()

        if node['xpos'].value() < x_min:
            x_min = node['xpos'].value()

        if node['ypos'].value() + node.screenHeight() > y_max:
            y_max = node['ypos'].value() + node.screenHeight()

        if node['ypos'].value() < y_min:
            y_min = node['ypos'].value()

    return int(x_min), int(x_max), int(y_min), int(y_max)



# #####################################################################

def get_comp_top_right():
    # Set global X_max & Y_min
    x_max = -4000
    y_min = 4000

    for node in nuke.allNodes():

        if node.Class() == 'BackdropNode':
            bd_x_max = node['bdwidth'].value() + node['xpos'].value()
            bd_y_min = node['ypos'].value()
            if bd_x_max > x_max:
                x_max = bd_x_max
            if bd_y_min < y_min:
                y_min = bd_y_min

        else:
            node_x_max = node.screenWidth() + node['xpos'].value()
            node_y_min = node['ypos'].value()
            if node_x_max > x_max:
                x_max = node_x_max
            if node_y_min < y_min:
                y_min = node_y_min

    return x_max, y_min




# #####################################################################

def readLighters():
    '''
    Return a list of lighters from a text file
    stored in the common directory (show-specific)
    '''
    proj = Project.current()
    projName = proj.name
    print projName

    lighters_file = '/work/%s/common/lighting/lighters.txt' % projName

    lighters_list = []

    # Check if file exists
    if os.path.isfile(lighters_file):

        # Read in the artists
        open_file = open(lighters_file, 'r')
        for line in open_file:
            lighters_list.append(line.strip())
        open_file.close()

        # Sort the list
        sorted_list = sorted(lighters_list)
        return sorted_list

    else:
        return None



# #####################################################################

def backdropArtists():
    '''
    Create a backdrop for each lighter.
    Used for casting
    '''
    sorted_artists = readLighters()
    proj = Project.current()
    projName = proj.name

    if not sorted_artists:
        lighters_file = '/work/%s/common/lighting/lighters.txt' % projName
        message = 'The file was not found!\n\n%s' % lighters_file
        nuke.message(message)

    else:

        # Find top right corner of comp
        x_max, y_min = get_comp_top_right()
        x_max += 500
        y_offset = 400

        for count, artist in enumerate(sorted_artists):

            this_y = y_min + (y_offset * count)
            this_x = x_max

            offset = 60
            font_diff = 50

            bd_x = this_x
            bd_y = this_y
            bd_w = 1000
            bd_h = 300

            # Create new Backdrop node
            artist_bd = nuke.createNode('BackdropNode', inpanel = False)
            artist_bd['xpos'].setValue(bd_x)
            artist_bd['ypos'].setValue(bd_y)
            artist_bd['bdwidth'].setValue(bd_w)
            artist_bd['bdheight'].setValue(bd_h)
            artist_bd['note_font_size'].setValue(40)
            artist_bd['label'].setValue(artist)
            artist_bd['tile_color'].setValue(1280068863)
            artist_bd['selected'].setValue(False)


# #####################################################################

def colorStatus(node, status):

    # Define default color
    color = nuke.defaultNodeColor(node.Class())
    cur_label = node['label'].value()


    if status == "pending":
        color = 4092851199
        new_label = '%s\n Pending' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "handoff":
        color = 4194304255
        new_label = '%s\n Ready for Handoff' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "artist":
        color = 1280068863
        new_label = '%s\n Ready for Artist' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "progress":
        color = 4169730815
        new_label = '%s\n In Progress' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "supervisor":
        color = 57087
        new_label = '%s\n Ready for Supe' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "digisup":
        color = 49212415
        new_label = '%s\n Ready for DigiSupe' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "director":
        color = 1325945087
        new_label = '%s\n Ready for Director' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "context":
        color = 4109567743
        new_label = '%s\n Ready for Context Review' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "cleanup":
        color = 1311974655
        new_label = '%s\n Ready for Cleanup' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "complete":
        color = 9896191
        new_label = '%s\n Complete!' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "onhold":
        color = 4093702911
        new_label = '%s\n On Hold' % (cur_label)
        node['label'].setValue(new_label)

    elif status == "omitted":
        color = 404297983
        new_label = '%s\n Omitted' % (cur_label)
        node['label'].setValue(new_label)

    # Assign the color
    try:
        node['tile_color'].setValue(color)
    except:
        pass


# #####################################################################
#                                                                     #
#                        INSIGHT FUNCTIONS                            #
#                                                                     #
# #####################################################################

def get_insight_data(seq_shot=None, discipline=None, task=None, version=None):
    '''
    Return a response object used to query relevant data.
    Note: seq_shot should be hyphenated: zzLOOK-0020
    '''
    user = getpass.getuser()
    proj = Project.current()
    projName = proj.name
    insightProj = projName.replace('_', '-')
    discipline_task = '%s/%s' % (discipline, task)

    # Ping Insight
    response = ipyapi.call(stage = 'production', port = 10400, name = 'find_shot_task_v1', params = {'api_client': 'nuke_contactSheet', 'api_key': '0173812c5ed97a93eb4d2e643976ec883717d3dd', 'current_user': user, 'project': insightProj, 'shot': seq_shot, 'task_slug': discipline_task})

    if response.code == 200:
        return response

    else:
        return None


def set_insight_status(seq_shot=None, discipline=None, task=None, task_status=None):
    '''
    Set status of a task in Insight
    '''
    user = getpass.getuser()
    proj = Project.current()
    projName = proj.name
    insightProj = projName.replace('_', '-')
    discipline_task = '%s/%s' % (discipline, task)

    response = ipyapi.call(stage = 'production', port = 10400, name = 'import_shot_task_v1', params = {'api_client': 'nuke_contactSheet', 'api_key': '0173812c5ed97a93eb4d2e643976ec883717d3dd', 'current_user': user, 'project': insightProj, 'shot': seq_shot, 'task_slug': discipline_task, 'status_slug': task_status})

    if response.code == 200:
        return True

    else:
        return False


def set_insight_comment(seq_shot=None, discipline=None, task=None, subject=None, body=None):
    '''
    Record a comment in given Insight task feed
    '''
    user = getpass.getuser()
    proj = Project.current()
    projName = proj.name
    insightProj = projName.replace('_', '-')
    discipline_task = '%s/%s' % (discipline, task)

    response = ipyapi.call(stage = 'production', port = 10400, name = 'create_shot_task_comment_v1', params = {'api_client': 'nuke_contactSheet', 'api_key': '0173812c5ed97a93eb4d2e643976ec883717d3dd', 'current_user': user, 'project': insightProj, 'shot': seq_shot, 'task_slug': discipline_task, 'subject': subject, 'body': body})

    if response.code == 200:
        return True

    else:
        return False


def colorReadStatus():

    print '\ncolorReadStatus()'
    # Get shot status from Insight & color the reads

    unique_shots = []
    updatedShots = []
    allReads = nuke.allNodes('Read')
    message = '\nUpdated Shots:\n\n'




    # Get reads list from selection
    read_list = nuke.selectedNodes('Read')
    if not read_list:
        nuke.message('\nNo \'Reads\' selected!\n')

    else:
        # Filter out duplicate shots from selection
        for item in read_list:
            this_shot = getSeqShotFromRead(item)

            if this_shot not in unique_shots:
                unique_shots.append(item)


        # Go through each unique shot
        for node in unique_shots:

            this_shot = getSeqShotFromRead(node)
            same_shots = []

            # Get other read nodes referencing this same shot
            for read in allReads:
                if getSeqShotFromRead(read) == this_shot:
                    same_shots.append(read)

            # Ping Insight for status
            response = get_insight_data(this_shot, discipline='lighting', task='lighting')

            if response:
                status = str(response.data['shot_task']['status_slug'])

                # Color the Reads
                for same_shot in same_shots:
                    colorStatus(same_shot, status)
                    this_string = '%s: %s' % (this_shot, status)
                    updatedShots.append(this_string)

        # Report results

        if updatedShots:
            multipleReads = []

            # sort the list
            sortedShots = sorted(updatedShots)

            for shot in sortedShots:
                # check if it's been counted already
                if shot not in multipleReads:
                    # count occurances of this shot
                    if sortedShots.count(shot) > 1:

                        multipleReads.append(shot)
                        message = message + shot + " (x%d)\n" % sortedShots.count(shot)

                    else:
                        message = message + shot + "\n"


# #####################################################################

def updateArtist(do_print=False):
    if do_print:
        print '\nupdateArtist()'
    # Get & record artist data from Insight

    unique_shots = []
    updatedShots = []
    allReads = nuke.allNodes('Read')
    message = '\nUpdated Shots:\n\n'

    # Get reads list from selection
    read_list = nuke.selectedNodes('Read')
    if not read_list:
        nuke.message('\nNo \'Reads\' selected!\n')

    else:
        # Filter out duplicate shots from selection
        for item in read_list:
            this_shot = getSeqShotFromRead(item)
            if this_shot not in unique_shots:
                unique_shots.append(item)

        # Go through each unique shot
        for node in unique_shots:

            this_shot = getSeqShotFromRead(node)
            same_shots = []

            # Get other read nodes referencing this same shot
            for read in allReads:
                if getSeqShotFromRead(read) == this_shot:
                    same_shots.append(read)

            # Ping Insight for assigned artist
            response = get_insight_data(this_shot, discipline='lighting', task='lighting')

            if response:
                artist = str(response.data['shot_task']['artist_user_name'])

                # Update the Reads
                for same_shot in same_shots:
                    if same_shot.knob('lighter'):
                        same_shot['lighter'].setValue(artist)
                        # Update label
                        if same_shot['label'].value() == '':
                            same_shot['label'].setValue('\n[value lighter]')
                            bump_up = same_shot.ypos() - 12
                            same_shot['ypos'].setValue(bump_up)

                        else:
                            nuke.message('\nArtist has not changed!\n')

                        this_string = '%s: %s' % (this_shot, artist)
                        updatedShots.append(this_string)


                    else:
                        lighter_knob = nuke.EvalString_Knob('lighter', 'Lighter:', artist)
                        same_shot.addKnob(lighter_knob)
                        # Update label
                        if same_shot['label'].value() == '':
                            same_shot['label'].setValue('\n[value lighter]')
                            bump_up = same_shot.ypos() - 12
                            same_shot['ypos'].setValue(bump_up)

                        else:
                            same_shot['label'].setValue('\n[value lighter]')

                        this_string = '%s: %s' % (this_shot, artist)
                        updatedShots.append(this_string)

        if do_print:
            # Report results
            message = "%d Reads updated\n\n" % len(updatedShots)

            if updatedShots:
                multipleReads = []

                # sort the list
                sortedShots = sorted(updatedShots)

                for shot in sortedShots:
                    # check if it's been counted already
                    if shot not in multipleReads:
                        # count occurances of this shot
                        if sortedShots.count(shot) > 1:

                            multipleReads.append(shot)
                            message = message + shot + " (x%d)\n" % sortedShots.count(shot)

                        else:
                            message = message + shot + "\n"

    if do_print:
        print 'Done\n'

# #####################################################################

def sortByShot():
    '''
    Sort the selected shots ascending Left to Right
    '''
    print '\nsortByShot()'

    # Get selected shots
    selected = nuke.selectedNodes('Read')

    if len(selected) == 0:
        nuke.message('\nNo \'Reads\' selected!\n')

    else:
        x_min, x_max, y_min, y_max = get_min_max(selected)
        shot_list = []

        # Deselect all
        for node in nuke.allNodes():
            node.setSelected(False)

        # Create list of shots & sort
        for read in selected:
            this_shot = getSeqShotFromRead(read)
            shot_list.append(this_shot)

        sorted_list = sorted(shot_list)
        offset = 120

        # Get nodes associated with each read
        for count, shot in enumerate(sorted_list):

            for read in selected:

                if getSeqShotFromRead(read) == shot:
                    #print '%s - %s: %d' % (read.name(), shot, count)
                    # clear dependent list
                    global dependent_nodes
                    dependent_nodes = []
                    getDependents(read)
                    dependent_nodes.append(read)

                    current_x = read['xpos'].value()
                    new_x = x_min + (offset * count)
                    xform = current_x - new_x

                    # Move all the dependents
                    for child in dependent_nodes:
                        child_orig_x = child['xpos'].value()
                        child['xpos'].setValue(child_orig_x - xform)

    print 'Done\n'


# #####################################################################

# #####################################################################

def insightComment():
    print '\ninsightComment()'
    # Flip 'Ready for Artist' in Insight & color the reads

    unique_shots = []
    unique_nodes = []
    updatedShots = []
    notUpdatedShots = []
    allReads = nuke.allNodes('Read')
    message = '\nComment Shots:\n\n'
    user = getpass.getuser()
    go_for_it = False

    proj = Project.current()
    projName = proj.name
    insightProj = projName.replace('_', '-')


    # Get reads list from selection
    read_list = nuke.selectedNodes('Read')

    if not read_list:
        nuke.message('\nNo \'Reads\' selected!\n')

    else:
        # Filter out duplicate shots from selection
        for node in read_list:
            this_shot = getSeqShotFromRead(node)
            if this_shot not in unique_shots:
                unique_shots.append(this_shot)
                unique_nodes.append(node)

        # Confirm whether comment is for all unique shots
        if len(unique_shots) > 1:
            warning = 'Apply the same comment for %d shots?' % len(unique_shots)
            if nuke.ask(warning):
                go_for_it = True

        elif len(unique_shots) == 1:
            go_for_it = True

        if go_for_it:
            # Build the panel first...
            feedback = 'Leave Comment for these shots:\n'

            for node in unique_nodes:
                # Check for lighter knob
                if not node.knob('lighter'):
                    # Get that lighter in there
                    for thing in nuke.allNodes():
                        thing.setSelected(False)
                    node.setSelected(True)
                    updateArtist(0) # call with zero to prevent prints

                this_artist = node['lighter'].value()
                this_shot = getSeqShotFromRead(node)
                feedback += '\n%s: %s' % (this_shot, this_artist)

            p = newCommentPanel(feedback)
            p.setMinimumSize(300, 500)
            result = p.showModalDialog()

            if not result:
                print '\nNevermind\n'

            else:
                # check values of UI panel
                if int(p.task.getValue()) == 0:
                    task_type = 'lighting/lighting'
                    task_select = 'lighting'
                else:
                    task_type = 'lighting/comp'
                    task_select = 'comp'

                subject = p.subject.getValue()
                body = p.note.getValue()

                # Go through each unique shot
                for node in unique_nodes:

                    this_shot = getSeqShotFromRead(node)

                    # Ping Insight for assigned artist
                    response = set_insight_comment(this_shot, discipline='lighting', task='%s' % (task_select), subject=subject, body=body)

                    if not response:
                        # Error
                        this_string = '%s' % this_shot
                        notUpdatedShots.append(this_string)

                    else:
                        # Success
                        this_string = '%s' % this_shot
                        updatedShots.append(this_string)

                # Report results

                message = "Notes added to: "

                # Order the successfully updated shots
                if updatedShots:
                    multipleReads = []

                    # sort the list
                    sortedShots = sorted(updatedShots)

                    for shot in sortedShots:
                        # check if it's been counted already
                        if shot not in multipleReads:
                            # count occurances of this shot
                            if sortedShots.count(shot) > 1:

                                multipleReads.append(shot)
                                message = message + shot + " (x%d)\n" % sortedShots.count(shot)

                            else:
                                message = message + shot + "\n"

                # Order the shot which failed to record the comments
                if notUpdatedShots:
                    multipleReads = []

                    # sort the list
                    sortedShots = sorted(notUpdatedShots)

                    for shot in sortedShots:
                        # check if it's been counted already
                        if shot not in multipleReads:
                            # count occurances of this shot
                            if sortedShots.count(shot) > 1:

                                multipleReads.append(shot)
                                message = message + shot + " (x%d)\n" % sortedShots.count(shot)

                            else:
                                message = message + shot + "\n"

                nuke.message(message)
    print 'Done\n'


# #####################################################################

class newCommentPanel(nukescripts.PythonPanel):

    def __init__(self, feedback):
        nukescripts.PythonPanel.__init__(self, 'Create Comment')
        self.setMinimumSize(300, 500)
        self.feedback = feedback
        self.feedback = nuke.Multiline_Eval_String_Knob('feedback', '', self.feedback)
        self.feedback.setFlag( nuke.READ_ONLY )
        self.task = nuke.Enumeration_Knob('task', 'Task:', ['Lighting', 'Comp'])
        self.subject = nuke.String_Knob('subject', 'Title:', '')
        self.note = nuke.Multiline_Eval_String_Knob('info', '', '')

        self.addKnob(self.feedback)
        self.addKnob(self.task)
        self.addKnob(self.subject)
        self.addKnob(self.note)



# #####################################################################

def insight_web_launch(seq_shot=None, user=None, projName=None, discipline=None, task=None):
    '''
    Open the Insight task for these shots in browser
    '''

    discipline_task = '%s/%s' % (discipline, task)

    # Ping Insight
    response = ipyapi.call(stage = 'production', port = 10400, name = 'find_shot_task_v1', params = {'api_client': 'nuke_contactSheet', 'api_key': '0173812c5ed97a93eb4d2e643976ec883717d3dd', 'current_user': user, 'project': projName, 'shot': seq_shot, 'task_slug': discipline_task})

    if response.code == 200:
        web_page = str(response.data['shot_task']['url'])

        # open it!
        wb = webbrowser.get()
        wb.open_new_tab(web_page)

    else:
        message = 'The URL could not be found!\n%s' % seq_shot
        nuke.message(message)


# #####################################################################

def insightWeb(task=None):
    # Check for no selection
    if not nuke.selectedNodes('Read'):
        nuke.message("\nNo reads selected!\n")

    else:
        if task == 0:
            task_type = 'lighting/lighting'
            do_it = True
            sel_task = 'lighting'

        else:
            task_type = 'lighting/comp'
            do_it = True
            sel_task = 'comp'

        # Many shots warning
        if len(nuke.selectedNodes('Read')) > 9:
            message = "\nYou are about to open %d tabs.\nWould you like to proceed?\n" % len(nuke.selectedNodes('Read'))

            if not nuke.ask(message):
                do_it = False


        if do_it:

            user = getpass.getuser()
            proj = Project.current()
            projName = proj.name
            insightProj = projName.replace('_', '-')

            # open the shots in Insight
            for read in nuke.selectedNodes('Read'):
                seq_shot = getSeqShotFromRead(read)
                insight_web_launch(seq_shot=seq_shot, user=user, projName=insightProj, discipline='lighting', task='%s' % sel_task)






