#include "include/stdlib.jsx" 

var docRef = null

main()

function main() {
        displayDialogs = DialogModes.NO

    if (documents.length == 0) {
        alert("There are no documents open.")
    }
    else {
        docRef = activeDocument
    }
    
    Stdlib.setPlaybackAccelerated()
    
    var win = new Window("dialog")
    g = win.graphics
    var myBrush = g.newBrush(g.BrushType.SOLID_COLOR, [0.99, 0.99, 0.99, 1])
    g.backgroundColor = myBrush
    win.title = win.add('statictext',undefined, 'Export Layers as TIFFs')
    var g = win.title.graphics
    win.p1  = win.add("panel", undefined, undefined, {borderStyle:"black"})
    win.p1.grp0 =  win.p1.add("group")
    win.p1.grp0.orientation='row'
    win.p1.grp0.alignChildren='fill'
    win.p1.grp0.spacing=10
    win.p1.grp0.st1 = win.p1.grp0.add('statictext',undefined,'Save Location:')
    win.p1.grp0.st1.helpTip= 'Select the location where the TIFs and backup of the PSD file will be saved'
    win.p1.grp0.et1 = win.p1.grp0.add('edittext')
    win.p1.grp0.et1.preferredSize=[300,20]
    var filePath = docRef.fullName.toString().split(docRef.name)[0]
    filePath = filePath.substring(0,filePath.length-1)
    filePath = filePath.replace(/paint$/,'proj')
    win.p1.grp0.et1.text = filePath
    win.p1.grp0.et1.active=true
    win.p1.grp0.bu1 = win.p1.grp0.add('button',undefined,'Browse...')
    win.p1.grp0.bu1.onClick = function() {
        var saveFolderRef = Folder.selectDialog ()
        if(saveFolderRef != null) {
            win.p1.grp0.et1.text = saveFolderRef.fullName
        }
    }
    win.p1.grp1 = win.p1.add("group")
    win.p1.grp1.orientation = 'row'
    win.p1.grp1.alignChildren = 'fill'
    win.p1.grp1.bu1 = win.p1.grp1.add('button',undefined,'Save Layers')
    win.p1.grp2 = win.p1.add("group")
    win.p1.grp2.orientation = 'row'
    win.p1.grp2.alignChildren = 'fill'
    win.p1.grp1.bu1.onClick = function() {
        win.p1.grp2.pb1 = win.p1.grp2.add('progressbar',[100,100,450,120],0,100)
        win.layout.layout(true)
        togglePalettes()
        var version = getNextVersionNum(win.p1.grp0.et1.text)
        var versionPad = zeroFill (version, 3)
        var nextVersionFolderRef = new Folder(win.p1.grp0.et1.text+"/v"+versionPad)
        nextVersionFolderRef.create()
        var nextFolderName = nextVersionFolderRef.fullName
        saveAllLayers(nextFolderName,win.p1.grp2.pb1)
        var copyPSDFile = new File(nextFolderName+"/"+docRef.name)
        var psdSaveOptions = new PhotoshopSaveOptions()
        psdSaveOptions.layers = true
        psdSaveOptions.alphaChannels = true
        docRef.saveAs(copyPSDFile,psdSaveOptions,true,Extension.LOWERCASE)
        win.p1.grp2.pb1.value = 100
        var linkRef = new File(win.p1.grp0.et1.text + "/live")
        if(linkRef.exists) {
            linkRef.remove()
        }
        linkRef = new File(win.p1.grp0.et1.text + "/live")
        linkRef.createAlias(nextFolderName)
        
        win.p1.grp2.remove(win.p1.grp2.pb1)
        togglePalettes()
    }

    win.show()
}

// Searches a given folder path for version sub-folders, and determines what the next
// version number to create should be.
function getNextVersionNum(folderPath) {
    function isVersionFolder(f) {
        // Folders do not open
        if (typeof f.open == "undefined" && f.name.match(/^v\d{3}$/) != null) {
            return true
        } else {
            return false
        }
    }
    folderRef = Folder(folderPath)
    versionFolders = folderRef.getFiles(isVersionFolder)
    //$.writeln(versionFolders.length+1)
    nextVersion = versionFolders.length + 1
    return parseInt(nextVersion)
}

function saveAllLayers(folderPath,progressBar) {
    var numLayers = docRef.layers.length

    var layerNames = []
    for(var i = 0; i < numLayers; i++) {
            var layerRef = docRef.layers[i]
            layerNames[i] = layerRef.name
    }
    
    var lastLayerRef = docRef.layers[docRef.layers.length-1]
    
    var exportNum = 0

    // Iterate over every layer and layer set (aka group) and export as TIFs
    for(var i =0; i < layerNames.length; i++) {
        var layerName = layerNames[i]
        var layerRef = docRef.layers.getByName(layerName)
        if(layerName.match(/^\s*-/)  != null || !layerRef.visible) {
            continue
        }
        // Force the layer to be selected, otherwise the duplicate function fails
        // with an internal error.
        selectLayer(layerName)
        saveLayerToTif(layerRef,exportNum,folderPath)
        exportNum++
        progressBar.value = (i/layerNames.length)*100
    }

    deselectLayers()
}

//Saves a layer to a Tif file
//Parameters:
//      layerRef = The given layer
//      num = the prefix number to use for the file name
//      folderPath = The folder path to save the TIFF into, if it is not provided
//                              the original document file path is used
function saveLayerToTif(layerRef,num,folderPath) {
    var newDocRef = documents.add(docRef.width,docRef.height)
    activeDocument = docRef
    var copyLayerRef = layerRef.duplicate(newDocRef)
    activeDocument = newDocRef
    if(copyLayerRef.typename == "LayerSet") {
        var mergedLayerRef = copyLayerRef.merge()
    }
    newDocRef.layers.getByName("Background").remove()
    var fullPath = docRef.fullName.toString()
    var pathTo = fullPath.split(docRef.name)[0]
    if(folderPath != "") {
            pathTo = folderPath + "/"
    }
    var prefixNum = zeroFill(num,3)
    var layerName = layerRef.name.replace(/\W/g, "_").toLowerCase()
    var layerFilePath = pathTo + prefixNum + "_" + layerName + ".tif"
    
    var tifFile = new File(layerFilePath)
    tifSaveOptions = new TiffSaveOptions()
    tifSaveOptions.alphaChannels = false
    tifSaveOptions.transparency = true
    tifSaveOptions.layers = true
    activeDocument.saveAs(tifFile, tifSaveOptions, false, Extension.LOWERCASE)
    activeDocument.close(SaveOptions.DONOTSAVECHANGES)
    
    activeDocument = docRef
}

// Deselect any layers currently selected in the list of layers
function deselectLayers() { 
    var desc01 = new ActionDescriptor(); 
        var ref01 = new ActionReference(); 
        ref01.putEnumerated( charIDToTypeID('Lyr '), charIDToTypeID('Ordn'), charIDToTypeID('Trgt') ); 
    desc01.putReference( charIDToTypeID('null'), ref01 ); 
    executeAction( stringIDToTypeID('selectNoLayers'), desc01, DialogModes.NO ); 
};

// Replaces any currently selected layer in the layer list with the layer of the given name
function selectLayer(layerName) {
    var ad = new ActionDescriptor()
    var ar = new ActionReference()
    ar.putName( charIDToTypeID("Lyr "), layerName)
    ad.putReference( charIDToTypeID( "null" ), ar );
    executeAction( charIDToTypeID( "slct" ), ad, DialogModes.NO)
}

// Pad a number with number of leading zero digits equal to width
function zeroFill( number, width )
{
  width -= number.toString().length;
  if ( width > 0 )
  {
    return new Array( width + (/\./.test( number ) ? 2 : 1) ).join( '0' ) + number;
  }
  return number + ""; // always return a string
}