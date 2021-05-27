#!/usr/bin/env python3

# download media to the media folder and add the data to the sources.csv automatically

import requests
from bs4 import BeautifulSoup
import click
from pathlib import Path
import pandas as pd
import os

def next_path(path_pattern):
    """
    Finds the next free path in an sequentially named list of files

    e.g. path_pattern = '%03d-results.tsv':

    001-results.tsv
    001-results.tsv
    """
    i = 1

    # First do an exponential search
    while Path(path_pattern % i).exists():
        i = i * 2

    # Result lies somewhere in the interval (i/2..i]
    # We call this interval (a..b] and narrow it down until a + 1 = b
    a, b = (i // 2, i)
    while a + 1 < b:
        c = (a + b) // 2  # interval midpoint
        a, b = (c, b) if Path(path_pattern % c).exists() else (a, c)

    return path_pattern % b

@click.group()
def main():
    pass

@main.command()
@click.argument('id')
@click.option('-n', '--name', 'science')
@click.option('-s','--save', is_flag=True)
@click.option('-r','--remove', is_flag=True)
def xeno(id, science, save, remove):
    if remove:
        remove_xeno(id)
    else:
        get_xeno(id, science, save)

def remove_xeno(id):
    df = pd.read_csv("sources.csv")

    if df.url.str.contains(id).any():
        row = df[df.url.str.contains(id)]
        os.remove(f"src/media/{row.iloc[0].filename}")
        print("Deleted file")
        print(row.index[0])
        df = df.drop(labels=row.index[0], axis=0)
        print(f"Deleted from sources.csv: {row.iloc[0].tolist()}")
        df.to_csv("sources.csv", index=False)
    else:
        print(f"{id} not found in sources.csv.")

def get_xeno(id, science, save):
    d = {}

    URL = f'https://www.xeno-canto.org/{id}'
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, 'html.parser')

    # URL
    d["url"] = URL

    # scientific name
    if science:
        name = science
    else:
        job_elems = soup.find_all('span', class_='scientific-name')
        name = job_elems[0].text
    d["name"] = name

    # type
    job_elems = soup.find_all('span', class_='jp-xc-call-type')
    if "call" in job_elems[0].text:
        mtype = "call"
    else:
        mtype = "song"
    d["media_type"] = mtype

    # filename
    name = "_".join(name.split())
    fname = next_path(
            f"src/media/{name}_{mtype}_" + "%01d.mp3")
    d["filename"] = fname.split("/")[-1]

    # recordist
    job_elems = soup.find_all('div', class_='jp-xc-recordist')
    d["user"] = "© " + job_elems[0].text

    # license
    job_elems = soup.find('td', class_='licenses')
    d["license"] = "https:"+ job_elems.find('a')['href']

    print(d)
    
    # mp3 download
    if save:
        df = pd.read_csv("sources.csv")
        if df.url.str.contains(id).any():
            print("Not downloaded! Already exists in sources.csv.")
        else:
            doc = requests.get(f"{URL}/download")
            with open(fname, 'wb') as f:
                    f.write(doc.content)

            df = df.append(d, ignore_index=True)
            df = df.reset_index(drop=True)
            df.to_csv("sources.csv", index=False)

            print("Saved successfully!")


if __name__ == "__main__":
    main()