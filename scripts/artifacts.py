try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

import json
import os
import re
import subprocess
import sys


def get_json(url):
    return json.loads(urlopen(url).read().decode('utf-8'))


def download_file(src_url, dest_path):
    print(dest_path)
    subprocess.call(
        ['curl', '-L', '-#', '-o', dest_path, src_url])


def download_appveyor_artifacts():
    api_url = 'https://ci.appveyor.com/api'
    builds = get_json(
        '{}/projects/etrepum/simplejson'.format(api_url))

    for job in builds['build']['jobs']:
        url = '{api_url}/buildjobs/{jobId}/artifacts'.format(
            api_url=api_url, **job)
        for artifact in get_json(url):
            download_file(
                '{url}/{fileName}'.format(url=url, **artifact),
                artifact['fileName'])


def download_github_artifacts():
    release = get_json(
        'https://api.github.com/repos/simplejson/simplejson/releases/latest')
    for asset in release['assets']:
        download_file(asset['browser_download_url'], 'dist/{name}'.format(**asset))

def get_version():
    return subprocess.check_output([sys.executable, 'setup.py', '--version']).strip()

def artifact_matcher(version):
    return re.compile('^simplejson-{}.*\\.(exe|whl)$'.format(re.escape(version)))

def sign_artifacts(version):
    artifacts = set(os.listdir('dist'))
    pattern = artifact_matcher(version)
    for fn in artifacts:
        if pattern.search(fn) and '{}.asc'.format(fn) not in artifacts:
            sign_artifact(os.path.join('dist', fn))

def sign_artifact(path):
    print(' '.join(['gpg', '--detach-sign', '-a', path]))
    subprocess.check_call(['gpg', '--detach-sign', '-a', path])

def upload_artifacts(version):
    artifacts = set(os.listdir('dist'))
    pattern = artifact_matcher(version)
    args = ['twine', 'upload']
    for fn in artifacts:
        if pattern.search(fn):
            filename = os.path.join('dist', fn)
            args.extend([filename, filename + '.asc'])
    subprocess.check_call(args)

def main():
    download_appveyor_artifacts()
    download_github_artifacts()
    version = get_version()
    sign_artifacts(version)
    upload_artifacts(version)


if __name__ == '__main__':
    main()
