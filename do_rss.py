import xml.etree.cElementTree as ET
from xml.dom import minidom
import os, sys, time
import shutil
from datetime import datetime
from mutagen.mp3 import MP3
from email.utils import formatdate
from time import gmtime
from time import strftime
import math

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

def wait_for_file(filepath):
    wait_time = 1
    while is_locked(filepath):
        print(filepath + ' is locked!!! Is it open in another program?')
        print('Please stop using the file and the program will continue!!!')
        time.sleep(wait_time)

def publish_all(sourcepath, destpath):
    dirs = os.listdir(sourcepath)

    if len(dirs) == 0:
        print('to_publish folder empty, skipping...')
        return 1
    print('Found files to publish:')
    print(dirs)

    for item in dirs:
        if os.path.isfile(sourcepath+item):
            if item.split('.')[-1].lower() in ('mp3', 'txt'):
                print('relocating ' + sourcepath + item + ' to ' + destpath)
                wait_for_file(sourcepath + item)
                shutil.move(sourcepath + item, destpath + item)

def get_dict(filepath):
    with open(filepath, 'r') as file:
        data = file.read().split('\n')
        dct = {}
        for x in data:
            if not data[0] == '#':
                if '=' in x:
                    vals = x.split('=', 1)
                    dct[vals[0].strip()] = vals[1].strip()
        return dct

def gen_RSS(sourcepath):
    cpops = get_dict('channel_properties.txt')
    root = ET.Element('rss', {'xmlns:itunes':'http://www.itunes.com/dtds/podcast-1.0.dtd',
                            'xmlns:media':'https://search.yahoo.com/mrss/',
                            'xmlns:dcterms':'https://purl.org/dc/terms/',
                            'xmlns:spotify': 'https://www.spotify.com/ns/rss',
                            'xmlns:psc':'https://podlove.org/simple-chapters/',
                            'xmlns:googleplay':'http://www.google.com/schemas/play-podcasts/1.0',
                            'version':'2.0'})
    channel = ET.SubElement(root, 'channel')
    ET.SubElement(channel, 'title').text = cpops['title']
    ET.SubElement(channel, 'description').text = cpops['description']
    ET.SubElement(channel, 'itunes:summary').text = cpops['summary']
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'link').text = 'http://www.InfinitySoup.github.io/'
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

    dirs = os.listdir(sourcepath)
    for item in dirs:
        if os.path.isfile(sourcepath+item):
            if item.split('.')[-1].lower() in ('txt'):
                data = get_dict(sourcepath + item)
                item = ET.SubElement(channel, 'item')
                ET.SubElement(item, 'title').text = data['title']
                ET.SubElement(item, 'description').text = data['description']
                ET.SubElement(item, 'pubDate').text = data['pubDate']
                ET.SubElement(item, 'duration').text = data['duration']
                ET.SubElement(item, 'enclosure', url=data['enclosure'], type='audio/mpeg', length=data['bytelength'])
                ET.SubElement(item, 'guid', isPermaLink='false').text=data['guid']


    # write to file
    tree = ET.ElementTree(root)
    # xml version tag is added in write()
    tree.write('feed.rss', encoding='UTF-8', xml_declaration=True)

    # debug printing
    import xml.dom.minidom
    dom = xml.dom.minidom.parse('feed.rss')
    print('\n')
    print(dom.toprettyxml())

def gen_descs(path, destpath):
    dirs = os.listdir(path)

    if len(dirs) == 0:
        print('No files found in source folder!')
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
                aud = MP3(path + item)
                print(aud.info.length)

                try:
                    epp = open(destpath + item.split('.')[0] + '.txt', 'x')
                    print('creating ' + item.split('.')[0] + '.txt')
                    epp.write('title=PLACEHOLDER EPISODE TITLE')
                    epp.write('\ndescription=PLACEHOLDER EPISODE DESCRIPTION')
                    epp.write('\nexplicit=no')
                    epp.write('\npubDate=' + formatdate())

                    epp.write('\n')
                    epp.write('\nenclosure=https://www.InfinitySoup.github.io/published/' + item.replace(' ', '_'))
                    epp.write('\nduration=' + strftime("%H:%M:%S", gmtime(math.ceil(aud.info.length))))
                    epp.write('\nguid=' + str(abs(hash(item + str(ts) + str(aud.info.length)))))
                    epp.write('\nbytelength=' + str(os.path.getsize(path + item)))
                    epp.close()
                    shutil.move(path + item, destpath + item.replace(' ', '_'))
                except FileExistsError:
                    print(item.split('.')[0] + '.txt already exists! skipping...')


gen_RSS('published/')
publish_all('to_publish/', 'published/')
gen_descs('raw_mp3s/', 'to_publish/')