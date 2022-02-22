import nuke
import re
import nkContact
import nkSel

def insightDropper( mimeType, text ):
  if mimeType == 'text/plain' and 'pro.reelfx.com' in text:
	seq_shot = re.search('\d\d\d\d-\d\d\d\d', text).group()
	if seq_shot:
	  seq, shot = seq_shot.split('-')
	  n = nkContact.compRead(seq=seq, shot=shot, ver='live')
	return True
  else:
	return None