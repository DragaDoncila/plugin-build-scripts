import os
from parse_meta_from_dists import clone_all, build_all, read_all
import pandas as pd
import matplotlib.pyplot as plt

clone_csv_pth = 'clone_times.csv'
build_csv_pth = 'build_times.csv'

root_pth = '/Users/ddoncilapop/CZI/plugins_demo/'
repo_pth = os.path.join(root_pth, 'repositories/')
pkg_pth = os.path.join(root_pth, 'packages/')

clone_all(repo_pth, clone_csv_pth)
build_all(repo_pth, pkg_pth, build_csv_pth)
read_all(pkg_pth)

df_clone = pd.read_csv(clone_csv_pth)
df_build = pd.read_csv(build_csv_pth)

# grab successful build and clone
clone_times = [df_clone[df_clone['clone_success'] == 1]['clone_time']]
build_time = [df_build[df_build['build_type'] == 'wheel']['build_time']]

# plot times
ax = plt.axes()
ax.hist(clone_times+build_time, histtype='bar', label=['Clone Repo', 'Build Wheel'])
ax.set_title('Time to Clone Repository and Build Wheel')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Count')
ax.legend(loc='best')
plt.show()

print(df_clone[df_clone['clone_time'] > 10]['plugin'])



