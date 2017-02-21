#!/usr/bin/env python

import sys
import subprocess
import json
import desdb
import pyfits

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
	Generate Random positions
	"""

	subprocess.call(['./SetTilename.py',__tilename__])
	subprocess.call(['./BuildPosGrid.py','--seed',__config__['seed_position'],'--density',__config__['density'],'--tiles','tilename.fits','--tilecol','tilename','--outdir','./'])

	return __tilename__+'.fits'

def GetZeropoint(RunConfig, DerivedConfig,BalrogConfig, ext=0, zpkey='SEXMGZPT'):
	if BalrogConfig['band']=='det':
		return 30.0
	else:
		header = pyfits.open(BalrogConfig['image'])[ext].header
		return header[zpkey]

def DoNosimRun(position_file,image_files,psf_files,bands):

	for band_ in xrange(len(bands)):
		band = bands[band_]
		img  = image_files[band_]
		psf  = psf_files[band_]
		
		


if __name__ == '__main__':


	with open(sys.argv[1]) as data_file:    
		__config__ = json.load(data_file)

	__tilename__ = sys.argv[2]

	print 'Starting tile:',__tilename__

	CopyAstrometry()
	print 'Copied astrometry files.'

	images, psfs, bands, = DownloadImages()
	print 'Downloaded images.'

	positions = GenerateRandomPosition()
	print 'Positions generated.'

	

	print 'Done tile:',__tilename__
