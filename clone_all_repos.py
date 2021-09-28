from parse_meta_from_dists import clone_all
import json

cloned_repos = clone_all('./repositories')
with open('repo_pths.json', 'w') as f:
    json.dump(cloned_repos, f)
