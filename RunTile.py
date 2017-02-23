#!/usr/bin/env python

import os
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
__detbands__ = ['r','i','z']

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
	command['poscat'] = '%s.fits' % __tilename__
	command['seed'] = __config__['seed_balrog']

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

	nosim_files = []
	nosim_cols  = []
	for band_ in xrange(1,len(bands)):
		nosim_files.append( pyfits.open('./%s/balrog_cat/DES2051-5248_%s.measuredcat.sim.fits'%(bands[band_],bands[band_]) )[2].data )

		for col_ in nosim_files[-1].columns:
			if col_.name != 'VECTOR_ASSOC':
				nosim_cols.append( pyfits.Column(name=(col_.name+'_'+bands[band_]).lower(), format=col_.format, array=nosim_files[-1][col_.name] ) )

	hdu = pyfits.BinTableHDU.from_columns( nosim_cols )
	hdu.writeto( '%s_nosim.fits'%__tilename__,clobber=True )

	#for band_ in xrange(1,len(bands)):
	#	subprocess.call( [ 'rm','-rf','./%s' % bands[band_] ] )
	

def RunSwarp(imgs, wts, iext=0, wext=1):
	config = {'RESAMPLE': 'N', \
              'COMBINE': 'Y', \
              'COMBINE_TYPE': 'CHI-MEAN', \
              'SUBTRACT_BACK': 'N', \
              'DELETE_TMPFILES': 'Y', \
              'WEIGHT_TYPE': 'MAP_WEIGHT', \
              'PIXELSCALE_TYPE': 'MANUAL', \
              'PIXEL_SCALE': str(0.270), \
              'CENTER_TYPE': 'MANUAL', \
              'HEADER_ONLY': 'N', \
              'WRITE_XML': 'N', \
              'VMEM_DIR': os.path.dirname(imgs[0]), \
              'MEM_MAX': '1024', \
              'COMBINE_BUFSIZE': '1024'}


	header = pyfits.open(imgs[0])[iext].header

	xsize  = header['NAXIS1']
	ysize  = header['NAXIS2']
	config['IMAGE_SIZE'] = '%i,%i' %(xsize,ysize)

	xc = header['CRVAL1']
	yc = header['CRVAL2']
	config['CENTER'] = '%f,%f' %(xc,yc)

	ims = []
	ws  = []
	for i in range(len(imgs)):
		ims.append( '%s[%i]' %(imgs[i],iext) )
		ws.append(  '%s[%i]' %(wts[i],wext)  )

	ims = ','.join(ims)
	ws  = ','.join(ws)
	
	subprocess.call(['mkdir','coadd'])

	imout = './coadd/%s_det.fits' % __tilename__
	wout  = imout.replace('.fits', '_weight.fits')
	config['IMAGEOUT_NAME']  = imout
	config['WEIGHTOUT_NAME'] = wout
    
	command = [__config__['swarp'], ims, '-c', __config__['swarp-config'], '-WEIGHT_IMAGE', ws]
	for key in config:
		command.append( '-%s'%(key) )
		command.append( config[key] )

	subprocess.call( command )

	return imout, wout

def BuildDetectionCoadd(position_file,image_files,psf_files,bands):
	command = {}
	command = __config__['balrog'].copy()
	command['imageonly']    = True
	command['noweightread'] = True

	ngal = len(pyfits.open( '%s.fits' % __tilename__)[1].data)
	command['ngal'] = ngal
	command['tile'] = __tilename__
	command['poscat'] = '%s.fits' % __tilename__
	command['seed'] = __config__['seed_balrog']

	ims = []
	wts = []
	for detband_ in __detbands__:
		command['psf']    = psf_files[__bands__.index(detband_)+1]
		command['image']  = image_files[__bands__.index(detband_)+1]
		command['outdir'] = './'+detband_+'/'
		command['band']   = detband_
		command['zeropoint'] = GetZeroPoint(image_files[__bands__.index(detband_)+1],detband_)

		RunBalrog(command)

		ims.append( './%s/balrog_image/DES2051-5248_%s.sim.fits' % (detband_,detband_) )
		wts.append( command['image'] )

	imout, wout = RunSwarp(ims,wts)

	return imout, wout
	
		
def DoSimRun(position_file,image_files,psf_files,bands,coadd_image, coadd_weights):
	command = {}
	command = __config__['balrog'].copy()
	command['nonosim']      = True
	command['noweightread'] = True
	command['nodraw']       = True

	ngal = len(pyfits.open( '%s.fits' % __tilename__)[1].data)
	command['ngal'] = ngal
	command['tile'] = __tilename__
	command['poscat'] = '%s.fits' % __tilename__
	command['seed'] = __config__['seed_balrog']

	for band_ in xrange(1,len(bands)):
		band = bands[band_]
		img  = image_files[band_]
		psf  = psf_files[band_]

		command['detpsf']    = psf_files[0]
		command['detimage']  = coadd_image
		command['detweight'] = coadd_weights
		command['psf'] = psf_files[band_]
		command['image'] = image_files[band_]
		command['outdir'] = './'+band+'/'
		command['zeropoint'] = GetZeroPoint(image_files[band_],band)
		command['band'] = band

		RunBalrog(command)

	nosim_files = []
	nosim_cols  = []
	for band_ in xrange(1,len(bands)):
		nosim_files.append( pyfits.open('./%s/balrog_cat/DES2051-5248_%s.measuredcat.sim.fits'%(bands[band_],bands[band_]) )[2].data )

		for col_ in nosim_files[-1].columns:
			if col_.name != 'VECTOR_ASSOC':
				nosim_cols.append( pyfits.Column(name=(col_.name+'_'+bands[band_]).lower(), format=col_.format, array=nosim_files[-1][col_.name] ) )

	hdu = pyfits.BinTableHDU.from_columns( nosim_cols )
	hdu.writeto( '%s_sim.fits'%__tilename__,clobber=True )

def StackTruth():
	nosim_files = []
	nosim_cols  = []
	for band_ in xrange(1,len(bands)):
		nosim_files.append( pyfits.open('./%s/balrog_cat/DES2051-5248_%s.truthcat.sim.fits'%(bands[band_],bands[band_]) )[2].data )

		for col_ in nosim_files[-1].columns:
			nosim_cols.append( pyfits.Column(name=(col_.name+'_'+bands[band_]).lower(), format=col_.format, array=nosim_files[-1][col_.name] ) )

	hdu = pyfits.BinTableHDU.from_columns( nosim_cols )
	hdu.writeto( '%s_truth.fits'%__tilename__,clobber=True )
	

def UploadToPersistentLocation():
	subprocess.call( ['ifdh','cp','%s_nosim.fits' % __tilename__,__config__['path_outfiles']] )
	subprocess.call( ['ifdh','cp','%s_sim.fits' % __tilename__,__config__['path_outfiles']] )
	subprocess.call( ['ifdh','cp','%s_truth.fits' % __tilename__,__config__['path_outfiles']] )



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
	print 'Nosim done.'

	coadd_image, coadd_weights = BuildDetectionCoadd(images,images,psfs,bands)
	print 'Coadd build.'
	
	DoSimRun(positions,images,psfs,bands,coadd_image, coadd_weights)
	print 'Sim done.'

	print 'Done tile:',__tilename__
