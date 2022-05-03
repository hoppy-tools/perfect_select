# Perfect Select
Perfect Select extends standard Blender selection tools.

## Features
Demo video: https://youtu.be/TCUGzs8SA_8
- selection snapping (with sliding on edge)
- extending selection to boundary loops
- preselections
- instant mirroring for select / deselect
- selection pattern from objects and images

## License
Perfect Select is under GPL license. You can use for free and customize the code for your needs.

## Releases
**This is developent branch.** Official releases are available to supporters on https://blendermarket.com/products/perfect-select.

## Building Guide
Part of this addon is written in C++ to improve performance. Compilation is not necessary but the benefits are significant.

### Prepare workspace
    mkdir ~/perfect_select_workspace
    mkdir ~/perfect_select_workspace/build
    cd ~/perfect_select_workspace

### Download Perfect Select sources
    git clone https://github.com/hophead-ninja/perfect_select.git

### Building without C++ backend (scripts only)
    cd ~/perfect_select_workspace/build
    cmake ../perfect_select -DBUILD_BACKEND=OFF
    make
Output files are located in `~/perfect_select_workspace/build/perfect_select`

### Building with C++ backend (Experimental - Linux only)
#### Download Blender sources (example for blender 2.83)
    mkdir -p ~/perfect_select_workspace/blender_sources/v2.83
    cd ~/perfect_select_workspace/blender_sources/v2.83
    git clone --branch v2.83 https://git.blender.org/blender.git
#### Download precompiled libs (mainly for python version compatibility)
    mkdir ~/perfect_select_workspace/blender_sources/v2.83/lib
    cd ~/perfect_select_workspace/blender_sources/v2.83/lib
    svn checkout https://svn.blender.org/svnroot/bf-blender/tags/blender-2.83-release/lib/linux_centos7_x86_64
#### Make and build
    cd ~/perfect_select_workspace/build
    cmake ../perfect_select -DBUILD_BACKEND=ON -DBLENDER_TAGS=v2.83
    make
Output files are located in `~/perfect_select_workspace/build/perfect_select`