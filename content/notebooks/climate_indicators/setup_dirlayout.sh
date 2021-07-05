#!/bin/sh -x

# Stable interface for the Jenkins testsuite to create any folders/files layout
# for the notebooks to be tested under Jenkins.  With this stable interface,
# Jenkins will not need to be modified for any future layout changes.
#
# Assume to be running inside the Jupyter env.

THIS_FILE="`realpath "$0"`"
THIS_DIR="`dirname "$THIS_FILE"`"

# Unzip notebook 3 output to avoid having to generate it during automated
# testing since it takes a long time.  Notebook 4 and 5 depend on this output.
NOTEBOOK_3_OUTDIR_BASE="/notebook_dir/writable-workspace/tmp/tutorial3"
mkdir -p $NOTEBOOK_3_OUTDIR_BASE
unzip $THIS_DIR/output.zip -d $NOTEBOOK_3_OUTDIR_BASE/

# Re-create /notebook_dir/pavics-homepage/tutorial_data layout for:
# DriverError: /notebook_dir/pavics-homepage/tutorial_data/test_regions.geojson: No such file or directory
#
# Path to those .geojson files are hardcoded so users can copy the nb to
# writable-workspace/ dir and still be able to run them seemlessly from
# the Jupyter env (without having to also copy those *.geojson files with
# the notebooks).
HOMEPAGE_ROOT_DIR="/notebook_dir/pavics-homepage"
mkdir -p $HOMEPAGE_ROOT_DIR
ln -sv $THIS_DIR/tutorial_data $HOMEPAGE_ROOT_DIR/tutorial_data
