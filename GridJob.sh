#!/usr/bin/env bash

OLDHOME=$HOME
export HOME=$PWD

touch log
date >> log

cat << EOF >> .netrc
machine leovip148.ncsa.uiuc.edu login $1 password $2
machine desar2.cosmology.illinois.edu login $1 password $2
EOF

chmod og-rwx .netrc 

unset EUPS_DIR
unset EUPS_PATH

/cvmfs/grid.cern.ch/util/cvmfs-uptodate /cvmfs/des.opensciencegrid.org
/cvmfs/grid.cern.ch/util/cvmfs-uptodate /cvmfs/lsst.opensciencegrid.org

source /cvmfs/des.opensciencegrid.org/eeups/startupcachejob21i.sh
export LSST_EUPS=/cvmfs/lsst.opensciencegrid.org/fnal/products
export DESREMOTE=https://desar2.cosmology.illinois.edu
export DESPROJ=DESFiles/desardata/OPS


# LSST eups path
export EUPS_PATH=$LSST_EUPS:$EUPS_PATH

setup sextractor 2.19.3+0
setup desdb
setup esutil
setup fitsio
setup suchyta_utils
setup healpy
setup balrog
setup Valarauko
setup fpack
setup swarp
setup scikitlearn


export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/cvmfs/lsst.opensciencegrid.org/uk/shape-measurement/im3shape/im3shape-2015-08-05/ups/lapack/v3_5_0/Linux64bit+2.6-2.12-e7-prof/lib:/cvmfs/lsst.opensciencegrid.org/uk/shape-measurement/im3shape/im3shape-2015-08-05/ups/gcc/v4_9_2/Linux64bit+2.6-2.12/lib64
export PYTHONPATH=${HOME}/Balrog:$PYTHONPATH

${HOME}/RunTile.py $3 $4

date >> log

export HOME=$OLDHOME
