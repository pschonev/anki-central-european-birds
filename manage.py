#!/usr/bin/env python3

# this script allows creation of the audio.csv and image.csv files from the source.csv, resizing images, checking database consistency and running Brain Brew

from pathlib import Path
from PIL import Image
import pandas as pd
import subprocess
import click
import sys
import os



@click.group()
def main():
    pass


def copy_file(path, name, number):
    # copies template files for song and call, so that only one of them has to be changed
    with open(path, 'r') as infile:
        out_path = path.replace(f"{name}1", f"{name}{number}")
        with open(out_path, 'w') as outfile:
            content = infile.read().replace(f"{name}1", f"{name}{number}")
            outfile.write(content)
    return out_path


def add_to_df(df, media, i, name, filename):
    # adds cells to new dataframe for audio
    rowIndex = df.index.str.startswith(name)
    df.loc[rowIndex, f"{media}_{i}"] = f"[sound:{filename}]"
    return df


def resize(files, new_size, path):
    # resize images to a maximum width or height
    margin = 5
    for item in files:
        if os.path.isfile(path+item):
            image = Image.open(path+item)
            file_path, extension = os.path.splitext(path+item)
            size = image.size

            if not (size[0] < new_size+margin and size[1] < new_size+margin):
                if size[0] >= size[1]:
                    new_image_width = int(size[1] / size[0] * new_size)
                    image = image.resize((new_size, new_image_width), Image.ANTIALIAS)

                    print(f"resized {file_path + extension} {size} --> {(new_size, new_image_width)}")
                else:
                    new_image_height = int(size[0] / size[1] * new_size)
                    image = image.resize((new_image_height, new_size), Image.ANTIALIAS)

                    print(f"resized {file_path + extension} {size} --> {(new_image_height, new_size)}")

                image.save(file_path + extension, 'JPEG', quality=85)


@main.command()
def source_to_csv():
    # source.csv split up to audio.csv and image.csv

    sourcescsv = "sources.csv"
    audiocsv = "src/data/audio.csv"
    imagecsv = "src/data/image.csv"

    df = pd.read_csv(sourcescsv)

    # audio
    columns = [f"song_{i}" for i in range(1,6)]+[f"call_{i}" for i in range(1,6)]
    df_audio = pd.DataFrame(index=df.name.unique(), columns=columns)

    for media in ["song", "call"]:
        for name in df.name.unique():
            dfm = df.where((df.name==name) & (df.media_type==media)).dropna(how="all").reset_index(drop=True)
            dfm[["name", "filename"]].apply(lambda row: add_to_df(df_audio, media, row.name+1, row[0], row[1]), axis=1)

    df_audio = df_audio.rename_axis('name').reset_index()

    # images
    image_types = [mt for mt in df.media_type.unique().tolist() if mt not in ['call', 'song']]
    df_image = df.where(df.media_type.isin(image_types)).dropna(how="all")
    df_image.filename = df_image.filename.apply(lambda x: f"<img src=\"{x}\">")
    df_image = df_image.pivot_table(values="filename", index=df_image.name, columns=df_image.media_type, aggfunc="|".join)

    print(df_audio)
    df_audio.to_csv(audiocsv)
    print(df_image)
    df_image.to_csv(imagecsv)

    print(f"\nMedia types found ({len(df.media_type.unique().tolist())}):")
    for mt in df.media_type.unique().tolist():
        print(mt)


@main.command()
def source_to_csv():
    # source.csv split up to audio.csv and image.csv
# %%
import pandas as pd 
import numpy as np

def translate(seq, tdict):
    try:
        words = seq.replace(" ","").split(",")
    except:
        return np.nan
    translated_words = [tdict[word] for word in words if word]
    try:
        translated_words = ", ".join(translated_words)
        return translated_words
    except TypeError:
        return np.nan


df = pd.read_csv("src/data/main.csv")
habitats = pd.read_csv("src/data/habitats.csv")
foods = pd.read_csv("src/data/foods.csv")

for lang in habitats.columns:
    translations = pd.Series(habitats[lang].values,habitats.en).to_dict()
    if lang != "en":
        df[f"habitat:{lang}"] = df["habitat:en"].map(
            lambda seq: translate(seq, translations),
            na_action="ignore")
for lang in foods.columns:
    translations = pd.Series(foods[lang].values,foods.en).to_dict()
    if lang != "en":
        df[f"food:{lang}"] = df["food:en"].map(
            lambda seq: translate(seq, translations),
            na_action="ignore")
df

# %%

@main.command()
@click.argument('recipe_path', type=click.Path(exists=True))
def brainbrew(recipe_path):
    # create templates for additional song and call fields, run brainbrew build option and delete templates
    created_files = []
    for i in range(2,6):
        created_files.append(copy_file("src/note_models/templates/Call1 - Name.html", "Call", i))
        created_files.append(copy_file("src/note_models/templates/Song1 - Name.html", "Song", i))

    print(f"Executing brainbrew on {recipe_path}")
    subprocess.check_call(["brain_brew", "run", recipe_path], stdout=sys.stdout, stderr=subprocess.STDOUT)

    for file in created_files:
        os.remove(file)

@main.command()
@click.option('-s', default=640)
def resize_images(s):
    # resize all images in media file to have a maximum length s for either side
    path = "src/media/"
    files = [x for x in os.listdir(path) if x.endswith(".jpg")]
    files = [x for x in files if not x.startswith("_")]
    resize(files, s, path)


@main.command()
def check_database():
    # checks database conistency between sources file and media folder
    filename = "sources.csv"
    df = pd.read_csv(filename)
    p = Path(r'src/media').glob('**/*')
    files = [x.name for x in p if x.is_file()]
    files = [x for x in files if not x.startswith("_")]

    print("\nIn media folder but not in source file:\n")
    for file in list(set(files) - set(df.filename.to_list())):
        print(file)
    print("\n\n---------------------------------\n\nIn source file but not in media folder:\n")
    for file in list(set(df.filename.to_list()) - set(files)):
        print(file)

if __name__ == "__main__":
    main()