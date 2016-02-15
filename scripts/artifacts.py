try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

import io
import json
import subprocess


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


def main():
    download_appveyor_artifacts()
    download_github_artifacts()


if __name__ == '__main__':
    main()
