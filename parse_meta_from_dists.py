import glob
import json
import os
from time import time
from git import Repo
import pandas as pd
import pkginfo
import requests
import subprocess
import sys

from collections import defaultdict
from pkginfo import Wheel, SDist
from tqdm.std import tqdm

PLUGINS_URL = 'https://api.napari-hub.org/plugins'
INDIVIDUAL_URL = lambda x: f'https://api.napari-hub.org/plugins/{x}'

def clone_repo(plugin_name, dest_dir, code_url=None):
    """Clones repository for the given plugin_name to dest_dir.

    If code_url is passed, clones from the given url, otherwise
    queries the napari hub API for this plugin's information and
    uses the code_repository field in the returned information.

    Parameters
    ----------
    plugin_name : str
        plugin whose repository to clone 
    dest_dir : str or Path-like
        destination directory for the repository

    Returns
    -------
    str or Path-like
        path to cloned repository
    """
    if code_url is None:
        #TODO: make request safe
        plugin_info = json.loads(requests.get(INDIVIDUAL_URL(plugin_name)).text.strip())
        code_url = plugin_info['code_repository']
    
    if code_url:
        try:
            Repo.clone_from(code_url, os.path.join(dest_dir, plugin_name))
        except Exception as e:
            # print(f"Unable to clone plugin {plugin_name} from {code_url}:\n")
            return None
        #TODO: this can be incorrect if the repository name is different to the plugin name
        return os.path.join(dest_dir, plugin_name)

def build_dist(pth, dest_dir):
    """Builds wheel for package found at `pth` if possible, otherwise source dist.

    Using the currently executing python interpreter, attempts to build a wheel
    from the package at `pth` and place it in a temp folder in your current
    working directory. If wheel build fails, attempts to build distribution
    from source.

    Parameters
    ----------
    pth : str
        path to root of python package
    dest_dir: str
        path to destination directory

    Returns
    -------
    tmp_dir : Path
        path to the temp directory where the distribution is stored

    Raises
    ------
    RuntimeError
        If a python binary cannot be found, or distribution cannot be built.
    """
    # get env binary where we're executing python
    ENVBIN = sys.exec_prefix

    # get the python binary from this env
    PYTHON_BIN = os.path.join(ENVBIN, "bin", "python")

    if not os.path.exists(PYTHON_BIN):
        raise RuntimeError(f"Cannot find python in {ENVBIN}.")

    full_pth = os.path.abspath(pth)

    current_dir = os.getcwd()
    os.chdir(full_pth)    
    # print(f"Building distribution for package at {full_pth}...")
    is_wheel = 0
    try:
        subprocess.run([PYTHON_BIN, 'setup.py', 'bdist_wheel', '--dist-dir', dest_dir], check=True, capture_output=True)
    except Exception as e:
        #TODO: improve error message here by capturing output from subprocess
        # print(f"Building wheel was unsuccessful: {e}.\nAttempting to build source distribution")
        try:
            subprocess.run([PYTHON_BIN, 'setup.py', 'sdist', '--dist-dir', dest_dir], check=True, capture_output=True)
        except Exception as e:
            # print(f"Building from source was unsuccessful: {e}.")
            os.chdir(current_dir)
            raise RuntimeError(f'Could not build distribution for package at {full_pth}')
        # else:
            # print(f"Successfully built source distribution for package at{full_pth}.\n")
    else:
        # print(f"Successfully built wheel for package at {full_pth}.")
        is_wheel = 1
    finally:
        os.chdir(current_dir)
    return is_wheel

def read_pkg_info(pkg_pth):
    """Parses and returns metadata of the wheel or sdist at pkg_pth.

    Parameters
    ----------
    pkg_pth : str or Path-like
        path to wheel or sdist

    Returns
    -------
    Dict[str, str | List[str]]
        dictionary matching fields to the parsed values
    """
    meta_needed = {        
        "name": 'name',
        "summary": 'summary',
        "description": 'description',
        "description_text": 'description',
        "description_content_type" : 'description_content_type',
        "authors" : 'author',
        "license" : 'license',
        "python_version": 'requires_python',
        "operating_system" : 'classifiers',
        "version": 'version',
        "development_status": 'classifiers',
        "requirements" : 'requires_dist',
        "project_site": 'home_page',
        "documentation": 'project_urls',
        "support": 'project_urls',
        "report_issues": 'project_urls',
        "twitter": 'project_urls',
        "code_repository": 'download_url'
    }

    meta = defaultdict()
    if os.path.basename(pkg_pth).endswith('.whl'):
        pkg_info = Wheel(pkg_pth)
    #TODO: make sure it ends with correct extension
    else:
        pkg_info = SDist(pkg_pth)
    #TODO: read what we can from config.yml
    #TODO: read description from .napari/DESCRIPTION.yml
    #TODO: get citations
    #TODO: get github license

    # split project URLS into dict 
    proj_urls = pkg_info.project_urls
    if proj_urls:
        proj_urls = [[val.strip() for val in url_str.split(',')] for url_str in proj_urls]
        proj_urls = dict(zip([url[0] for url in proj_urls], [url[1] for url in proj_urls]))
        pkg_info.project_urls = proj_urls

    for field, attr  in meta_needed.items():
        val = getattr(pkg_info, attr)
        if attr == 'project_urls':
            if field in val:
                meta[field] = val[field]
        elif attr == 'classifiers':
            if val:
                if field == 'operating_system':
                    meta[field] = list(filter(lambda x: x.startswith('Operating System'), val))
                elif field == 'development_status':
                    meta[field] = list(filter(lambda x: x.startswith('Development Status'), val))
            else:
                meta[field] = None
        elif attr == 'requires_dist':
            reqs = getattr(pkg_info, attr)
            for i, req in enumerate(reqs):
                if '; extra ==' in req:
                    reqs[i] = req.split('; extra ==')[0].strip()
            meta[field] = reqs
        else:
            meta[field] = getattr(pkg_info, attr)
    return meta

def read_extra_requirements(pkg_info):
    all_requirements = pkg_info.requires_dist
    extra_requirements = defaultdict(lambda: [])

    extra_str = ' ; extra == '

    for req in all_requirements:
        if extra_str in req:
            package, extra_field = tuple(req.split(extra_str))
            extra_requirements[extra_field].append(package)
    
    return extra_requirements

def clone_all(dest_pth, out_csv_pth=None):
    """Clones repositories of all currently listed napari hub plugins.

    Queries napari hub API for all currently listed plugins and attempts
    to clone their repositories to dest_pth. Outputs plugin names, 
    whether cloning was successful and the time to clone to `clone_times.csv`
    at dest_path.

    Parameters
    ----------
    dest_pth : str or Path-like
        directory to clone repositories into
    out_csv_pth: Optional str or Path-like
        path to save clone times to, by default None
    """
    clone_time = []
    pass_fail = []

    all_plugins = sorted(list(json.loads(requests.get(PLUGINS_URL).text.strip()).keys()))
    for plugin in tqdm(all_plugins, desc='Cloning Repositories'):
        start = time()
        dest_dir = clone_repo(plugin, dest_pth)
        duration = time() - start
        clone_time.append(duration)
        if dest_dir:
            pass_fail.append(1)
        else:
            pass_fail.append(0)

    clone_df = pd.DataFrame({'plugin': all_plugins, 'clone_success': pass_fail, 'clone_time': clone_time})
    if out_csv_pth:
        clone_df.to_csv(out_csv_pth)

def build_all(plugin_dir, dest_dir, out_csv_pth):
    """Builds distribution in dest_dir for all plugins in plugin_dir.

    Attempts to build distribution for all plugin repositories in
    plugin_dir. Outputs plugin names, build type (wheel or sdist)
    and time to build to `build_times.csv` in dest_dir.

    Parameters
    ----------
    plugin_dir : str or Path-like
        path to directory containing one or more plugin repositories
    dest_dir : str or Path-like
        directory to place distribution files
    out_csv_pth: str or Path-like
        path to save build time csv
    """
    all_plugins = sorted(glob.glob(f"{plugin_dir}/*/"))

    build_info = []
    for plugin_pth in tqdm(all_plugins, 'Building Packages'):
        plugin_name = os.path.dirname(plugin_pth).split('/')[-1]
        if os.path.isdir(plugin_pth):
            start = time()
            try:
                is_wheel = build_dist(plugin_pth, dest_dir)
                duration = time() - start
                if is_wheel:
                    build_info.append((plugin_name, 'wheel', duration))
                else:
                    build_info.append((plugin_name, 'src', duration))
            except RuntimeError:
                duration = time() - start
                build_info.append((plugin_name, 'fail', duration))
    
    all_plugins, all_builds, all_times = zip(*build_info)
    df = pd.DataFrame({'plugin': all_plugins, 'build_type': all_builds, 'build_time': all_times})
    df.to_csv(out_csv_pth)

def format_meta_str(meta):
    meta_str = ''
    fields = sorted(list(meta.keys()))
    first_desc = 0
    for field in fields:
        if 'description' in field:
            if first_desc == 0:
                meta_str += f"{field.title()}:\n {meta[field][:100]}\n"
                first_desc = 1
        elif field == 'name':
            name = meta[field]
            if '_' in name:
                name = '-'.join(name.split('_'))
            meta_str += f"{field.title()}:\n {name}\n"
        else:
            meta_str += f"{field.replace('_', ' ').title()}:\n {meta[field]}\n"
        meta_str+= '\n'
    return meta_str

def read_all(pkg_pths):
    all_wheels = sorted(glob.glob(pkg_pths+'*.whl'))
    all_srcs = sorted(glob.glob(pkg_pths+"*.tar.gz"))

    wheel_meta = {}
    for whl_pth in tqdm(all_wheels, 'Reading Metadata'):
        meta = read_pkg_info(whl_pth)
        wheel_meta[meta['name']] = meta

    src_meta = {}
    if all_srcs:
        for src_pth in tqdm(all_srcs):
            meta = read_pkg_info(src_pth)
            plugin_name = meta['name']
            # src dists seem to build with underscores not dashes. Replace them for now
            if '_' in plugin_name:
                plugin_name = '-'.join(plugin_name.split('_'))
            src_meta[plugin_name] = meta   

    return wheel_meta
