#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2021, OpenEmbedded for Tegra Project
#
# Adapted from: https://github.com/OE4T/meta-tegra-community/blob/97813c33460513aad02ae65509954ad32f3d26bf/recipes-test/tegra-tests/vpi3-tests/run-vpi3-tests.sh

# Added 19_dcf_tracker sample (exists in VPI3 L4T container but not in OE4T test suite)
# NOTE: PVA backend removed from benchmark — NGC docs say VPI does not support PVA backend in containers

SAMPLEROOT="/opt/nvidia/vpi3/samples"
SAMPLEASSETS="$SAMPLEROOT/assets"
SKIPCODE=97

for d in $SAMPLEROOT/*; do
    PATH="$PATH:$d/build"
done

run_convolve_2d() {
    echo "Running 01_convolve_2d - Backend is $1"
    vpi_sample_01_convolve_2d "$1" "$SAMPLEASSETS/kodim08.png"
}

run_stereo_disparity() {
    echo "Running 02_stereo_disparity - Backend is $1"
    vpi_sample_02_stereo_disparity "$1" "$SAMPLEASSETS/chair_stereo_left.png" "$SAMPLEASSETS/chair_stereo_right.png"
}

run_harris_corners() {
    echo "Running 03_harris_corners - Backend is $1"
    vpi_sample_03_harris_corners "$1" "$SAMPLEASSETS/kodim08.png"
}

run_rescale() {
    echo "Running 04_rescale - Backend is $1"
    vpi_sample_04_rescale "$1" "$SAMPLEASSETS/kodim08.png"
}

run_benchmark() {
    echo "Running 05_benchmark - Backend is $1"
    vpi_sample_05_benchmark "$1"
}

run_klt_tracker() {
    echo "Running 06_klt_tracker - Backend is $1"
    vpi_sample_06_klt_tracker "$1" "$SAMPLEASSETS/dashcam.mp4" "$SAMPLEASSETS/dashcam_bboxes.txt"
}

run_fft() {
    echo "Running 07_fft - Backend is $1"
    vpi_sample_07_fft "$1" "$SAMPLEASSETS/kodim08.png"
}

run_tnr() {
    echo "Running 09_tnr - Backend is $1"
    vpi_sample_09_tnr "$1" "$SAMPLEASSETS/noisy.mp4"
}

run_perspwarp() {
    echo "Running 10_perspwarp - Backend is $1"
    vpi_sample_10_perspwarp "$1" "$SAMPLEASSETS/noisy.mp4"
}

run_fisheye() {
    # TODO: graphical sample, may need display
    echo "Running 11_fisheye"
    vpi_sample_11_fisheye -c 10,7 -s 22 "$SAMPLEASSETS/fisheye/"*.jpg
}

run_optflow_lk() {
    echo "Running 12_optflow_lk - Backend is $1"
    vpi_sample_12_optflow_lk "$1" "$SAMPLEASSETS/dashcam.mp4" 5 frame.png
}

run_optflow_dense() {
    echo "Running 13_optflow_dense"
    vpi_sample_13_optflow_dense "$1" "$SAMPLEASSETS/pedestrians.mp4" high 1 5
}

run_background_subtractor() {
    echo "Running 14_background_subtractor - Backend is $1"
    vpi_sample_14_background_subtractor "$1" "$SAMPLEASSETS/pedestrians.mp4"
}

run_image_view() {
    # TODO: graphical sample, skip when no display
    echo "Running 15_image_view - Backend is $1"
    vpi_sample_15_image_view "$SAMPLEASSETS/kodim08.png"
}

run_template_matching() {
    echo "Running 17_template_matching - Backend is $1"
    vpi_sample_17_template_matching "$1" "$SAMPLEASSETS/kodim08.png" "100,200,100,100"
}

run_orb_feature_detector() {
    echo "Running 18_orb_feature_detector - Backend is $1"
    vpi_sample_18_orb_feature_detector "$1" "$SAMPLEASSETS/kodim08.png"
}

run_dcf_tracker() {
    echo "Running 19_dcf_tracker - Backend is $1"
    vpi_sample_19_dcf_tracker "$1" "$SAMPLEASSETS/pedestrians.mp4" "$SAMPLEASSETS/pedestrians_bboxes.txt"
}

# VPI samples list (17 total)
TESTS="convolve_2d stereo_disparity harris_corners rescale benchmark"
TESTS="$TESTS klt_tracker fft tnr perspwarp fisheye optflow_lk optflow_dense"
TESTS="$TESTS background_subtractor image_view template_matching orb_feature_detector dcf_tracker"

# List of VPI backends per sample app
convolve_2d=("cpu" "cuda")
stereo_disparity=("cuda" "ofa" "ofa-pva-vic")
harris_corners=("cpu" "cuda")
rescale=("cpu" "cuda" "vic")
# pva backend: NGC warns "VPI does not support PVA backend within containers" (Docker --runtime nvidia)
# but should work with Podman CDI (--device nvidia.com/gpu=all) + PVA auth disable on host
benchmark=("cpu" "cuda" "pva")
klt_tracker=("cpu" "cuda")
fft=("cpu" "cuda")
tnr=("cuda" "vic")
perspwarp=("cpu" "cuda" "vic")
fisheye=("cuda")
optflow_lk=("cpu" "cuda")
optflow_dense=("ofa")
background_subtractor=("cpu" "cuda")
image_view=("cpu")
template_matching=("cpu" "cuda")
orb_feature_detector=("cpu" "cuda")
# pva backend: NGC warns "VPI does not support PVA backend within containers"
# dcf_tracker: pva backend fails with VPI_ERROR_INVALID_IMAGE_FORMAT in containers
dcf_tracker=("cuda")

find_test() {
    for t in $TESTS; do
    if [ "$t" = "$1" ]; then
        echo "$t"
        return
    fi
    done
}

testcount=0
testpass=0
testfail=0
testskip=0
if [ $# -eq 0 ]; then
    tests_to_run="$TESTS"
else
    tests_to_run="$@"
fi

# SKIP_BACKENDS env var: comma-separated list of backends to skip (e.g., "pva,ofa,ofa-pva-vic")
# Used by test_basic_pva.py to skip backends not supported on the hardware (e.g., Nano has no PVA/OFA)
skip_backend() {
    local backend="$1"
    for skip in $(echo "${SKIP_BACKENDS:-}" | tr ',' ' '); do
        [ "$backend" = "$skip" ] && return 0
    done
    return 1
}

for cand in $tests_to_run; do
    t=$(find_test "$cand")
    if [ -z "$t" ]; then
        echo "ERR: unknown test: $cand" >&2
    else
        declare -n backendList=$t
        for backend in ${backendList[@]}; do
            if skip_backend "$backend"; then
                echo "=== SKIP:  $t ($backend) — backend not available on this hardware ==="
                testskip=$((testskip+1))
                testcount=$((testcount+1))
                continue
            fi
            testcount=$((testcount+1))
            echo "=== BEGIN: $t ($backend) ==="
            if run_$t $backend; then
                echo "=== PASS:  $t ($backend) ==="
                testpass=$((testpass+1))
            elif [ $? -eq $SKIPCODE ]; then
                echo "=== SKIP:  $t ($backend) ==="
                testskip=$((testskip+1))
                break
            else
                echo "=== FAIL:  $t ($backend) ==="
                testfail=$((testfail+1))
            fi
        done
    fi
done

echo "Tests run:     $testcount"
echo "Tests passed:  $testpass"
echo "Tests skipped: $testskip"
echo "Tests failed:  $testfail"
exit $testfail
