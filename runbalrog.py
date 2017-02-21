import balrog

def RunBalrog(d):
	cmd = []

	for key in d.keys():
		if type(d[key])==bool:
			if d[key]:
				cmd.append('--%s' %key)
	else:
		cmd.append('--%s' %key)
		cmd.append(str(d[key]))

	balrog.BalrogFunction(args=cmd, syslog=__config__['log'])

