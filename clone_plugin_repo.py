from parse_meta_from_dists import clone_repo
import sys


plugin_name = sys.argv[1]
repo_pth = clone_repo(plugin_name, '.')
print(repo_pth)
