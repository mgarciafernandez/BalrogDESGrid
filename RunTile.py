#!/usr/bin/env python

import sys
import subprocess
import json
import desdb
import pyfits
import balrog

#------------------ GLOBAL VARIABLES ---------------

__config__   = None
__tilename__ = None
__bands__    = ['g','r','i','z','Y']

#---------------------------------------------------

def CopyAstrometry():
	"""
	Copy the SExtractor, zeropoints & SWARP config files to the current working node.
	"""

	subprocess.call(['ifdh','cp','-D',__config__['path_astrometry'],'./'])
	subprocess.call(['ifdh','cp','-D',__config__['path_slr'],'./'])
	subprocess.call(['ifdh','cp','-D',__config__['path_incat'],'./'])

	subprocess.call(['tar','-zxvf',__config__['path_astrometry'].split('/')[-1],'--strip-components','1'])

def DownloadImages():
	"""
	Read from the database where are the images and PSF files at the database and downloads them into the working node. Then uncompress the files with funpack.
	"""

	df = desdb.files.DESFiles(fs='net')
	conn = desdb.connect()
	
	images = []
	psfs   = []
	bands  = []

	for band_ in ['det']+__bands__:
		if band_ == 'det':
			d = conn.quick("SELECT c.run from coadd c, runtag rt where rt.run=c.run and c.tilename='%s' and rt.tag='%s' and c.band is null" % (__tilename__, __config__['data_release'].upper()), array=True)
		else:
			d = conn.quick("SELECT c.run from coadd c, runtag rt where rt.run=c.run and c.tilename='%s' and rt.tag='%s' and c.band='%s'" % (__tilename__, __config__['data_release'].upper(),band_), array=True)

		if len(d) == 0:
			continue

		img = df.url('coadd_image', coadd_run=d[0]['run'], tilename=__tilename__, band=band_)
		images.append( img )
		psfs.append( img.replace('.fits.fz', '_psfcat.psf') )
		bands.append( band_ )
		
		


	for image_ in images:
		subprocess.call(['wget','--quiet','--no-check-certificate',image_,'-O',image_.split('/')[-1]])
		subprocess.call(['funpack','-v','-D','-O',image_.split('/')[-1].replace('.fits.fz', '.fits'),image_.split('/')[-1]])
	for psf_ in psfs:
		subprocess.call(['wget','--quiet','--no-check-certificate',psf_,'-O',psf_.split('/')[-1]])
	return [ images, psfs, bands ]

def GenerateRandomPosition():
	"""
	Generate Random positions and sets at the config file the number of galaxies of the tile.
	"""
	subprocess.call(['rm','-f','tilename.fits',__tilename__+'.fits'])

	subprocess.call(['./SetTilename.py',__tilename__])
	subprocess.call(['./BuildPosGrid.py','--seed',str(__config__['seed_position']),'--density',str(__config__['density']),'--tiles','tilename.fits','--tilecol','tilename','--outdir','./','--iterateby','1'])

	return __tilename__+'.fits'

def GetZeroPoint(image,band, ext=0, zpkey='SEXMGZPT'):
	if band == 'det':
		return 30.0
	else:
		header = pyfits.open(image)[ext].header
		return header[zpkey]

def RunBalrog(d):
	cmd = []

	for key in d.keys():
		if type(d[key])==bool:
			if d[key]:
				cmd.append('--%s' %key)
		else:
			cmd.append('--%s' %key)
			cmd.append(str(d[key]))

	balrog.BalrogFunction(args=cmd)

def DoNosimRun(position_file,image_files,psf_files,bands):

	command = {}
	command = __config__['balrog'].copy()
	command['imageonly'] = False
	command['nodraw'] = True
	command['nonosim'] = True

	ngal = len(pyfits.open( '%s.fits' % __tilename__)[1].data)
	command['ngal'] = ngal
	command['tile'] = __tilename__
	command['slr']  = __config__['path_slr'].split('/')[-1]
	command['cat']  = __config__['path_incat'].split('/')[-1]
	command['poscat'] = '%s.fits' % __tilename__

	for band_ in xrange(1,len(bands)):
		band = bands[band_]
		img  = image_files[band_]
		psf  = psf_files[band_]

		command['detpsf'] = psf_files[0]
		command['detimage'] = image_files[0]
		command['psf'] = psf_files[band_]
		command['image'] = image_files[band_]
		command['outdir'] = './'+band+'/'
		command['zeropoint'] = GetZeroPoint(image_files[band_],band)
		command['band'] = band

		RunBalrog(command)
		

if __name__ == '__main__':


	with open(sys.argv[1]) as data_file:    
		__config__ = json.load(data_file)

	__tilename__ = sys.argv[2]

	print 'Starting tile:',__tilename__

	CopyAstrometry()
	print 'Copied astrometry files.'

	images, psfs, bands = DownloadImages()
	for image_ in xrange(len(images)):
		images[image_] = images[image_].split('/')[-1].replace('.fits.fz','.fits')
	for psf_ in xrange(len(psfs)):
		psfs[psf_] = psfs[psf_].split('/')[-1]
	print 'Downloaded images.'

	#positions = GenerateRandomPosition()
	positions = __tilename__+'.fits'
	print 'Positions generated.'

	DoNosimRun(positions,images,psfs,bands)

	print 'Done tile:',__tilename__
