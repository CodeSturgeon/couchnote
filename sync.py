#!/usr/bin/env python

import os.path
import couchdb
from couchdb import schema
from datetime import datetime
server = couchdb.Server('http://localhost:5984/')
db = server['noteish']

import pickle
import hashlib

import logging
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)

meta_store = {}
scan_dir = '/Users/fish/Documents/Notes'

class CouchNote(schema.Document):
    summary = schema.TextField()
    detail = schema.TextField()
    file_path = schema.TextField()
    last_update_time = schema.DateTimeField(default=datetime.now)
    #udpate_notes = TextField() # going to tai chi, more of a status message?
    implements = schema.DictField(
        schema.Schema.build(couchnote = schema.BooleanField(default = True)))

def save_note(meta, detail):
    # FIXME Missing md5
    if meta.has_key('id'):
        note = CouchNote.load(db, meta['id'])
        note.summary = meta['summary']
        note.file_path = meta['file_path']
        log.info('Updating note: %s'%meta['file_path'])
        # if note.rev != meta['rev']: ask_user()
    else:
        # warn about duplicat summary
        # if len(db.view('couchapp/summaries', key=meta['summary'])) > 0:
        # ask_user()
        log.info('New note: %s'%meta['file_path'])
        try:
            note = CouchNote(detail = detail, **meta)
        except UnicodeDecodeError:
            log.error('Could not import %s'%meta['summary'])
            return
    note.store(db)
    meta['id'] = note.id
    meta['rev'] = note.rev
    set_meta(meta['file_path'], meta)

def load_store():
    global meta_store
    if os.path.isfile('meta.cache'):
        meta_store = pickle.load(open('meta.cache'))
    else:
        open('meta.cache','w').close()

def save_store():
    global meta_store
    pickle.dump(meta_store, open('meta.cache','w'))

def ask_user(question):
    # UI abstraction, return true or false
    pass

def set_meta(file_path, meta):
    global meta_store
    # Save the file's couch meta data
    meta_store[file_path] = meta

def get_meta(path):
    # FIXME shoud be able to pass a couchnote... or is that make_meta?
    global meta_store
    if meta_store.has_key(path):
        return meta_store[path]
    else:
        meta = {}
        meta['file_path'] = path
        meta['summary'] = os.path.basename(path[:path.rfind('.')])
        return meta

def sync_dir(scan_dir):
    local_changes = []
    for root, dirs, files in os.walk(scan_dir):
        log.info('Scanning %s'%root)
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext == '.txt':
                full_path = os.path.join(root,file)
                rel_path = full_path[len(scan_dir):].lstrip('/')
                content = open(full_path).read()
                md5 = hashlib.md5(content).hexdigest()
                meta = get_meta(rel_path)
                if md5 != meta.get('md5',''):
                    local_changes.append(rel_path)
    return local_changes

def download_note(path):
    # Get doc_id from view
    doc_id = db.view('couchnote/paths', key=path).rows[0]['id']
    note = CouchNote.load(db, doc_id)
    open(os.path.join(scan_dir, note.file_path).'w').write(note.detail)
    meta = get_meta(note.file_path)
    meta['md5'] = hashlib.md5(content).hexdigest()
    meta['id'] = note.id
    meta['rev'] = note.rev
    meta['summary'] = note.summary
    set_meta(meta)

def get_couch_updates():
    remote_changes = []
    for row in db.view('couchnote/paths'):
        local_meta = get_meta(row['key'])
        if local_meta.get('rev','') == row['value']:
            continue
        remote_changes.append(path)
    return remote_changes
         

def main():
    load_store()
# get list of locally changed/new files...
    local_changes = sync_dir(scan_dir)
# get list of changed/new couch docs...
    remote_changes = get_couch_updates()
# apply anything that does not conflict
    conflicts = []
    for path in local_change:
        if path not in remote_changes:
            save_note(path)
        else:
            conflicts.append(path)
    for path in remote_changes:
        if path not in conflicts:
            download_note(path)
    for path in conflicts:
        log.error('Conflict with file %s'%path)
    save_store()

if __name__ == '__main__':
    main()
