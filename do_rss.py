import xml.etree.cElementTree as ET
from xml.dom import minidom
import os, sys, time
import shutil
from datetime import datetime
from mutagen.mp3 import MP3
import mutagen
from mutagen.easyid3 import EasyID3
from email.utils import formatdate
from time import gmtime
from time import strftime
import math

# returns True if a file is in use
def is_locked(filepath):
    locked = None
    file_object = None
    if os.path.exists(filepath):
        try:
            buffer_size = 8
            # Opening file in append mode and read the first 8 characters.
            file_object = open(filepath, 'a', buffer_size)
            if file_object:
                locked = False
        except IOError as message:
            locked = True
        finally:
            if file_object:
                file_object.close()
    return locked

# Waits for a file to no longer be in use (uses time.sleep())
def wait_for_file(filepath):
    wait_time = 1
    while is_locked(filepath):
        print(filepath + ' is locked!!! Is it open in another program?')
        print('Please stop using the file and the program will continue!!!')
        time.sleep(wait_time)

# Reads a plaintext file. Lines are split by the first equals sign on them into a dictionary.
# If a line has no equals signs, or starts with '#', the line is ignored.
def get_dict(filepath):
    with open(filepath, 'r') as file:
        data = file.read().split('\n')
        dct = {}
        for x in data:
            if not data[0] == '#':
                if '=' in x:
                    vals = x.split('=', 1)
                    dct[vals[0].strip().lower()] = vals[1].strip()
        return dct

# Load global channel properties
cpops = get_dict('channel_properties.txt')

# Validates integrity of .mp3 files and moves them and their descriptions to the "published" folder
def publish_all(sourcepath, destpath):
    dirs = os.listdir(sourcepath)

    if len(dirs) == 0:
        print('\'to publish\' folder empty, skipping...')
        return 1
    print('Found files to publish:')
    print(dirs)

    # Fix .mp3 file metadata (ID3 tags)
    for item in dirs:
        if os.path.isfile(sourcepath+item):
            if item.split('.')[-1].lower() in ('txt'):
                if 'txt' in item:
                    mp3name = sourcepath + '.'.join(item.split('.')[:-1]) + '.mp3'
                    mp3name = mp3name.replace(' ', '_')
                    try:
                        meta = EasyID3(mp3name)
                    except mutagen.id3.ID3NoHeaderError:
                        print('No ID3 tags found in' + mp3name + 'adding genre, title, and artist tags...')
                        meta = mutagen.File(mp3name, easy=True)
                        meta.add_tags()
                        meta['title'] = get_dict(sourcepath+item)['title']
                        meta['artist'] = cpops['artist']
                        meta['genre'] = 'Podcast'
                        meta.save(mp3name, v1=2)

    # move everything
    for item in dirs:
        if os.path.isfile(sourcepath+item):
            if item.split('.')[-1].lower() in ('mp3', 'txt'):
                print('relocating ' + sourcepath + item + ' to ' + destpath)
                wait_for_file(sourcepath + item)
                shutil.move(sourcepath + item, destpath + item)

# Generates the RSS feed according to Spotify's standards
def gen_RSS(sourcepath):
    # root properties
    root = ET.Element('rss', {'xmlns:itunes':'http://www.itunes.com/dtds/podcast-1.0.dtd',
                            'xmlns:media':'https://search.yahoo.com/mrss/',
                            'xmlns:dcterms':'https://purl.org/dc/terms/',
                            'xmlns:spotify': 'https://www.spotify.com/ns/rss',
                            'xmlns:psc':'https://podlove.org/simple-chapters/',
                            'xmlns:googleplay':'http://www.google.com/schemas/play-podcasts/1.0',
                            'version':'2.0'})
    channel = ET.SubElement(root, 'channel')
    # channel-wide properties
    ET.SubElement(channel, 'title').text = cpops['title']
    ET.SubElement(channel, 'description').text = cpops['description']
    ET.SubElement(channel, 'itunes:summary').text = cpops['summary']
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'link').text = 'http://InfinitySoup.github.io/'
    ET.SubElement(channel, 'itunes:author').text = cpops['author']
    ET.SubElement(channel, 'itunes:explicit').text = cpops['explicit']
    img = ET.SubElement(channel, 'image')
    ET.SubElement(img, 'url').text = cpops['image']
    owner = ET.SubElement(channel, 'itunes:owner')
    ET.SubElement(owner, 'itunes:email').text = cpops['email']
    ET.SubElement(owner, 'name').text = cpops['author']
    ET.SubElement(channel, 'itunes:image', href=cpops['image'])
    ET.SubElement(channel, 'itunes:type').text = cpops['type']
    ET.SubElement(channel, 'itunes:category', text=cpops['category'])
    ET.SubElement(channel, 'spotify:countryOfOrigin').text = 'us'

    # per-item properties
    dirs = os.listdir(sourcepath)
    for item in dirs:
        if os.path.isfile(sourcepath+item):
            if item.split('.')[-1].lower() in ('txt'):
                data = get_dict(sourcepath + item)
                item = ET.SubElement(channel, 'item')
                ET.SubElement(item, 'title').text = data['title']
                ET.SubElement(item, 'description').text = data['description']
                ET.SubElement(item, 'pubDate').text = data['pubdate']
                ET.SubElement(item, 'duration').text = data['duration']
                ET.SubElement(item, 'enclosure', url=data['enclosure'], type='audio/mpeg', length=data['bytelength'])
                ET.SubElement(item, 'guid', isPermaLink='false').text=data['guid']


    # write to file
    tree = ET.ElementTree(root)
    # xml version tag is added in write()
    tree.write('feed.rss', encoding='UTF-8', xml_declaration=True)

    # Show nicely printed XML:
    import xml.dom.minidom
    dom = xml.dom.minidom.parse('feed.rss')
    print('\nRSS GENERATED:\n')
    print(dom.toprettyxml())
    print('\n')

# Generates description files from .mp3 files.
# These .txt "description" files are used to write metadata onto the RSS feed
# A better approach might be to use .mp3 metadata for everything, but I think that
# this is the easiest way to do this without writing a UI.
def gen_descs(path, destpath):
    dirs = os.listdir(path)

    if len(dirs) == 0:
        print('\'raw mp3\' folder empty, skipping...')
        return 1
    print('Found files in source folder:')
    print(dirs)
    for item in dirs:
        if os.path.isfile(path+item):
            if item.split('.')[-1].lower() in ('mp3'):
                print('Checking to see if ' + path + item + ' exists...')
                wait_for_file(path + item)
                f, e = os.path.splitext(path + item)
                ts = os.path.getmtime(path + item)
                aud = MP3(path + item) # used to determine length of mp3 file

                # skip if the description already exists (this shouldn't happen, but just in case)
                try:
                    epp = open(destpath + item.replace(' ', '_').split('.')[0] + '.txt', 'x')
                    print('creating ' + item.replace(' ', '_').split('.')[0] + '.txt')
                    epp.write('title=PLACEHOLDER EPISODE TITLE')
                    epp.write('\ndescription=PLACEHOLDER EPISODE DESCRIPTION')
                    epp.write('\nexplicit=no')
                    epp.write('\npubDate=' + formatdate())

                    epp.write('\n')
                    epp.write('\nenclosure=https://InfinitySoup.github.io/published/' + item.replace(' ', '_'))
                    epp.write('\nduration=' + strftime("%H:%M:%S", gmtime(math.ceil(aud.info.length))))

                    # generate a (hopefully) unique and stable identifier from the filename and mp3 length
                    epp.write('\nguid=' + str(abs(hash(item.replace(' ', '_') + str(aud.info.length)))))
                    epp.write('\nbytelength=' + str(os.path.getsize(path + item)))
                    epp.close()
                    shutil.move(path + item, destpath + item.replace(' ', '_'))
                except FileExistsError:
                    print(item.split('.')[0] + '.txt already exists! skipping...')


if __name__ == '__main__':
    #publish_all('to_publish/', 'published/')
    #gen_RSS('published/')
    #gen_descs('raw_mp3s/', 'to_publish/')

    print('\n\nHey there!')
    print('Welcome to the Github Pages Podcast RSS Feed Generator.')
    input('Press [ENTER] to continue...')
    input(
        '\nOkay, step one: Put your NEW .mp3 files into the \'raw_mp3s\' folder in this directory.\nPress [ENTER] once you\'ve done this.\n')

    import os, time

    dirs = os.listdir('raw_mp3s')
    lin = ''
    while len(dirs) == 0 and lin.lower() != 'skip':
        lin = input('Hmm. I don\'t see anything in the \'raw_mp3s\' folder. Try again, and press [ENTER] when you\'re ready.\nOr, if you\'d like to skip this step, type \'skip\' and press [ENTER].\n')
        dirs = os.listdir('raw_mp3s')

    if lin.lower() != 'skip':
        print('Great! Hang on...')
        time.sleep(0.2)
        gen_descs('raw_mp3s/', 'to_publish/')
        print('\nOkay! Now, in the \'to_publish\' folder, you should a text file for each of your mp3s.')
        print('These text files are how you can set titles and descriptions of tracks, along with some other information.')
        input('EDIT THOSE TEXT FILES, and when you\'re satisfied with the changes, press [ENTER]')
    else:
        dirs = os.listdir('to_publish')
        lin = ''
        while len(dirs) == 0 and lin.lower() != 'skip':
            lin = input('Hmm. I don\'t see anything in the \'to_publish\' folder. Try again, and press [ENTER] when you\'re ready.\nOr, if you\'d like to skip this step, type \'skip\' and press [ENTER].\n')

    if lin.lower() != 'skip':
        print('Are you sure that you\'re satisfied with your changes the text files? This information cannot be changed once entered!')
        input('Press [ENTER] to confirm.\n')

        print('Cool! Just a second...')

        publish_all('to_publish/', 'published/')
        gen_RSS('published/')

        strr = input('\nYour RSS has been created! Would you like to publish it online? (y/n)\n')
        if len(strr) > 0 and strr[0] == 'y':
            print('Publishing to Github...')