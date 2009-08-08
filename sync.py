#!/usr/bin/env python
# bump
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
logging.basicConfig(level=logging.DEBUG)

meta_store = {}
scan_dir = './test_notes'
default_cache_filepath = './meta.cache'

class CouchNote(schema.Document):
    summary = schema.TextField()
    detail = schema.TextField()
    file_path = schema.TextField()
    last_update_time = schema.DateTimeField(default=datetime.now)
    #udpate_notes = TextField() # going to tai chi, more of a status message?
    implements = schema.DictField(
        schema.Schema.build(couchnote = schema.BooleanField(default = True)))

def upload_note(meta, detail):
    log.info('Uploading %s'%meta['file_path'])
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
    meta_store[meta['file_path']] = meta

def load_store(cache_filepath=default_cache_filepath):
    global meta_store
    if os.path.isfile(cache_filepath):
        meta_store = pickle.load(open(cache_filepath))

def save_store(cache_filepath=default_cache_filepath):
    if not os.path.isfile(cache_filepath):
        open(cache_filepath,'w').close()
    pickle.dump(meta_store, open(cache_filepath,'w'))

def ask_user(question):
    # UI abstraction, return true or false
    pass

def get_new_local(scan_dir):
    local_new = []
    for root, dirs, files in os.walk(scan_dir):
        log.info('Scanning %s'%root)
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext == '.txt':
                full_path = os.path.join(root,file)
                rel_path = full_path[len(scan_dir):].lstrip('/')
                if meta_store.has_key(rel_path):
                    local_new.append(rel_path)
    return local_new

def download_note(paths):
    if not isinstance(path, type([])):
        # Allow a single path to be passed as well as a list
        paths = [paths]
    for path in paths:
        # Get doc_id from view
        log.info('Downloading %s'%path)
        doc_id = db.view('couchnote/paths', key=path).rows[0]['id']
        note = CouchNote.load(db, doc_id)
        file_dir = os.path.join(scan_dir, os.path.split(note.file_path)[0])
        if file_dir != '':
            if not os.path.isdir(file_dir):
                log.info('Making dir: %s'%file_dir)
                os.makedirs(file_dir)
        open(os.path.join(scan_dir, note.file_path),'w').write(note.detail)
        meta = {}
        meta['md5'] = hashlib.md5(note.detail).hexdigest()
        meta['id'] = note.id
        meta['rev'] = note.rev
        meta['file_path'] = note.file_path
        meta['summary'] = note.summary
        meta_store[note.file_path] = meta

def get_couch_new_changed():
    remote_changes = []
    for row in db.view('couchnote/paths'):
        local_meta = meta_store.get(row['key'],{})
        if local_meta.get('rev','') == row['value']:
            continue
        remote_changes.append(row['key'])
    return remote_changes

def get_couch_changed():
    remote_changes = []
    ids = {}
    for path in meta_store:
        ids[meta_store[path]['id']] = {'path': path,
                                       'rev': meta_store[path]['rev']}
    for row in db.view('_all_docs', keys=ids.keys()):
        if ids[row['id']]['rev'] != row['value']['rev']:
            log.info(
                'Linked Couch Document changed: %s'%ids[row['id']]['path'])
            remote_changes.append(ids[row['id']]['path'])
    return remote_changes

def get_local_changed():
    local_changes = []
    kill_list = []
    for path in meta_store:
        full_path = os.path.join(scan_dir,path)
        if not os.path.isfile(full_path):
            log.warn('File gone: %s'%path)
            kill_list.append(path)
            continue
        md5 = hashlib.md5(open(full_path).read()).hexdigest()
        if meta_store[path]['md5'] != md5:
            log.info('Local file changed: %s'%path)
            local_changes.append(path)
    for killed in kill_list:
        del meta_store[killed]
    return local_changes

def main():
    load_store()
    local_changes = get_local_changed()
    remote_changes = get_couch_changed()
    conflicts = []
    upload = []
    download = []
    for path in local_changes:
        if path not in remote_changes:
            upload.append(path)
        else:
            conflicts.append(path)
    for path in remote_changes:
        if path not in conflicts:
            download.append(path)

    print 'Uploading: %s'%upload
    print 'Downloading: %s'%download
    print 'Conlifting: %s'%conflicts

    #map(download_note, download)
    save_store()

def old_main():
    load_store()
# get list of locally changed/new files...
    local_changes = sync_dir(scan_dir)
# get list of changed/new couch docs...
    remote_changes = get_couch_updates()
# apply anything that does not conflict
    conflicts = []
    for path in local_changes:
        if path not in remote_changes:
            upload_note(path)
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
