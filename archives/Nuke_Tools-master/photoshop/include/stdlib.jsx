cTID = function(s) { return app.charIDToTypeID(s); };
sTID = function(s) { return app.stringIDToTypeID(s); };

Stdlib = function Stdlib() {};

Stdlib.setActionPlaybackOptions = function(opt, arg) {
  function _ftn() {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putProperty(cTID("Prpr"), cTID("PbkO"));
    ref.putEnumerated(cTID("capp"), cTID("Ordn"), cTID("Trgt"));
    desc.putReference(cTID("null"), ref );
    var pdesc = new ActionDescriptor();
    pdesc.putEnumerated(sTID("performance"), sTID("performance"), sTID(opt));
    if (opt == "pause" && arg != undefined) {
      pdesc.putInteger(sTID("pause"), parseInt(arg));
    }
    desc.putObject(cTID("T   "), cTID("PbkO"), pdesc );
    executeAction(cTID("setd"), desc, DialogModes.NO);
  }
  _ftn();
};
Stdlib.setPlaybackAccelerated = function() {
  Stdlib.setActionPlaybackOptions("accelerated");
};
Stdlib.setPlaybackStepByStep = function() {
  Stdlib.setActionPlaybackOptions("stepByStep");
};
Stdlib.setPlaybackPaused = function(delaySec) {
  Stdlib.setActionPlaybackOptions("pause", delaySec);
};