try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
import json
import subprocess

api_url = 'https://ci.appveyor.com/api'
builds = json.load(urlopen(
    '{}/projects/etrepum/simplejson'.format(api_url)))

def artifact_url(job):
    return '{api_url}/buildjobs/{jobId}/artifacts'.format(
        api_url=api_url, **job)

for job in builds['build']['jobs']:
    url = artifact_url(job)
    for artifact in json.load(urlopen(url)):
        download_url = '{url}/{fileName}'.format(url=url, **artifact)
        print(artifact['fileName'])
        subprocess.call(
            ['curl', '-L', '-#', '-o', artifact['fileName'], download_url])
