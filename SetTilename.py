#!/usr/bin/env python

import sys
from astropy.io import fits

if __name__ == "__main__":
	tbhdu = fits.BinTableHDU.from_columns([ fits.Column(name='tilename',format='20A',array=[sys.argv[1]])] )
	tbhdu.writeto('tilename.fits')
