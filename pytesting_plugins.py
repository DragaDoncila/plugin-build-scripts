
from posix import listdir
from parse_meta_from_dists import read_extra_requirements, read_pkg_info
import os
from pkginfo import Wheel
import glob

repo_pth = '/Users/ddoncilapop/CZI/testing_plugins/repositories/'
whl_pth = '/Users/ddoncilapop/CZI/testing_plugins/wheels/'

aics_repo = os.path.join(repo_pth, 'napari-aicsimageio/')
aics_pkg = os.path.join(whl_pth, 'napari_aicsimageio-0.4.1-py2.py3-none-any.whl')

all_wheels = glob.glob(os.path.join(whl_pth, '*.whl'))
count_req = 0
count_test_dep = 0
count_dev_dep = 0
count_none = 0
for whl_pth in all_wheels:
    pkg_info = Wheel(whl_pth)
    extras = read_extra_requirements(pkg_info)
    meta = read_pkg_info(whl_pth)
    if 'pytest' in meta['requirements'] or 'tox' in meta['requirements']:
        # print(meta['requirements'])
        count_req += 1
    elif "'test'" in extras:
        # print(extras["'test'"])
        count_test_dep += 1
    elif "'dev'" in extras:
        for req in extras["'dev'"]:
            if 'pytest' in req or 'tox' in req:
                # print(extras["'dev'"])
                count_dev_dep += 1
    else:
        count_none += 1
        print(whl_pth)
print(count_none)

count_tox_ini = 0
all_repos = list(filter(lambda x: os.path.isdir(os.path.join(repo_pth, x)), listdir(repo_pth)))
for repo in all_repos:
    pth = os.path.join(repo_pth, repo)
    ini_files = glob.glob(os.path.join(pth, '**/tox.ini'), recursive=True)
    if ini_files:
        count_tox_ini += 1
    else:
        print(repo, ini_files)
print(count_tox_ini)

    
