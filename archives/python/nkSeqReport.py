import os
import qb
import sys
import nuke
import getpass
import nkReport
import nkAlign
import time
import threading
import xml
import rfxUtils

#constants
DEPARTMENT = 'entertainment'
PROJECT = '18842_turkeys_production'
LIGHTING_TASK_ID = '3'
	
def runReport(script,firstrun):
  reportList = nkReport.fullCompReport()
  #fix bad reporting of upstream and non-right-angle
  #flawedReports = [report for report in reportList if report['description'] == 'nodes with non-right-angle inputs' or report['description'] == 'nodes with downstream inputs']
  #for report in flawedReports:
	#reportList.remove(report)
  gradeTup = nkReport.masterGrade(reportList)
  #priorityOnes = nkReport.reportsByKey('priority', 1, reportList)
  badPriorityOnes = nkReport.reportsByKey('grade', 'BAD', reportList)
  shot = nuke.root()['shot'].getValue()
  seq = nuke.root()['seq'].getValue()
  jobid = os.environ.get('QBJOBID')
  job = qb.jobinfo(id=jobid)
  curUser = job[0].user()
  tasks = rfxUtils.get_tasks_for_shot(DEPARTMENT, PROJECT, seq, shot, LIGHTING_TASK_ID)
  tree = xml.etree.cElementTree.fromstring(tasks)
  for item in tree.getiterator('Task'):
	  supervisor_id = item.get('SupervisorID')
	  worker_id = item.get('WorkerID')
	  user_info = rfxUtils.getInsightUserInfo(userid=worker_id)
  for ui in user_info:
	assignedTo = user_info[ui]['fullName']
	emailTo = user_info[ui]['email']
  sys.stderr.write(('*' * 20) + '\n')
  sys.stderr.write('running check on %s\n' % script)
  sys.stderr.write(('*' * 20) + '\n')
  reportPath = ('/data/entertainment/18842_turkeys_production/cg/common/comp_reports/' + curUser)
  if firstrun:
	writemode = "w"
	if not os.path.exists(reportPath):
	  os.makedirs(reportPath)
	firstrun = False
  else:
	writemode = "a"
  with open(reportPath + '/seq_%s_report.txt' % seq, writemode) as reportTxt:
	reportTxt.write(('*' * 20) + '\n')
	reportTxt.write('Shot %s:\n' % shot)
	reportTxt.write('User: %s\n' % assignedTo)
	reportTxt.write('Email: %s\n' % emailTo)
	reportTxt.write('\nGRADE: %s %s%%:\n\n' % (gradeTup[0], gradeTup[2]))
	if len(badPriorityOnes) > 0:
	  for bpo in badPriorityOnes:
		reportTxt.write('Problem: %s %s\n' % (bpo['count'], bpo['description']))
	reportTxt.write(('*' * 20) + '\n\n')
  
  test = 0

def nodeReport(scripts):
  firstrun = True
  for script in scripts:
	if not os.path.exists(script):
	  continue
	nuke.scriptClear()
	nuke.scriptOpen(script)
	[nuke.delete(n) for n in nuke.allNodes() if n.Class() == 'Viewer']
	nuke.root().begin()
	runReport(script,firstrun)
	firstrun = False

if __name__ == '__main__':
  nodeReport(sys.argv[1:])
  sys.exit(0)