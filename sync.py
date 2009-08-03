#!/usr/bin/env python

import os.path
import couchdb
from couchdb import schema
from datetime import datetime
server = couchdb.Server('http://localhost:5984/')
db = server['noteish']

import logging
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

class CouchNote(schema.Document):
    summary = schema.TextField()
    detail = schema.TextField()
    file_path = schema.TextField()
    last_update_time = schema.DateTimeField(default=datetime.now)
    #udpate_notes = TextField() # going to tai chi, more of a status message?
    implements = schema.DictField(
        schema.Schema.build(couchnote = schema.BooleanField(default = True)))

def save_note(doc_dict):
    if doc_dict.has_key('id'):
        note = CouchNote.load(db, doc_dict['id'])
        note.detail = doc_dict['detail']
        note.summary = doc_dict['summary']
        # if note.rev != doc_dict['rev']: ask_user()
    else:
        # warn about duplicat summary
        # if len(db.view('couchapp/summaries', key=doc_dict['summary'])) > 0:
        # ask_user()
        log.debug('Making note: %s'%str(doc_dict))
        try:
            note = CouchNote(**doc_dict)
        except UnicodeDecodeError:
            log.error('Could not import %s'%doc_dict['summary'])
            return
    note.store(db)

def ask_user(question):
    # UI abstraction, return true or false
    pass

def get_meta(source_file_path):
    # Meta data store abstraction
    # Load dict from sqlite
    pass

def import_file(path, base_path):
    log.info('Importing %s'%path)
    doc_dict = {}
    doc_dict['file_path'] = path[len(base_path):]
    doc_dict['summary'] = os.path.basename(path[:path.rfind('.')])
    content = open(path).read()
    doc_dict['detail'] = content
    save_note(doc_dict)

def import_dir(scan_dir):
    for root, dirs, files in os.walk(scan_dir):
        log.info('Scanning %s'%root)
        for file in files:
            ext = file[file.rfind('.')+1:]
            if ext == 'txt':
                import_file(os.path.join(root,file), base_path=scan_dir)

def main():
    #note = 'ramma lamma happy feet 2'
    #meta = {'summary':'my first nope', 'id':'43e9c9f150a28b3e4be73203f84a10be'}
    #meta['detail'] = note
    #save_note(meta)
# note_ext = extract_ext(filename)
# note_meta['format'] = format_from_ext(note_ext)
    scan_dir = '/Users/fish/Documents/Notes'
    import_dir(scan_dir)


if __name__ == '__main__':
    main()
# for note in db
# compair local copy to db copy
# Locally in the file? In sqlite?
