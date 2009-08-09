#!/usr/bin/env python

import os.path
import couchdb
server = couchdb.Server('http://localhost:5984/')
db = server['noteish']

import hashlib

from store import MetaStore
from model import CouchNote

import logging
log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

scan_dir = './test_notes'

def upload_note(id, store):
    meta = store.get_meta(id)
    log.info('Updating note: %s'%meta['file_path'])
    note = CouchNote.load(db, meta['id'])
    meta['rev'] = note.rev
    note.detail = open(meta['file_path']).read()
    note.store(db)
    store.update_metas((note, meta['file_path']))

def new_note(file_path):
    # split path
    # make summary and file_path
    # make and save note
    # put in store
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

def download_notes(ids, store):
    note_paths = []
    for note_id in ids:
        # Get note_id from view
        log.info('Downloading %s'%note_id)
        note = CouchNote.load(db, note_id)
        file_dir = os.path.join(scan_dir, os.path.split(note.file_path)[0])
        if file_dir != '':
            if not os.path.isdir(file_dir):
                log.info('Making dir: %s'%file_dir)
                os.makedirs(file_dir)
        open(os.path.join(scan_dir, note.file_path),'w').write(note.detail)
        note_paths.append((note, note.file_path))
    store.update_metas(note_paths)

def get_couch_new(store):
    remote_changes = []
    ids = store.ids()
    for row in db.view('couchnote/paths'):
        if row['id'] not in ids:
            remote_changes.append(row['id'])
    return remote_changes

def get_couch_changed(store):
    remote_changes = []
    ids = store.ids()
    for row in db.view('_all_docs', keys=ids):
        meta = store.get_meta(row['id'])
        if meta['rev'] != row['value']['rev']:
            log.info('Linked Couch Document changed: %s'%meta['file_path'])
            remote_changes.append(row['id'])
    return remote_changes

def get_local_changed(store):
    local_changes = []
    kill_list = []
    for note_id, meta in store.store.iteritems():
        full_path = os.path.join(scan_dir,meta['file_path'])
        if not os.path.isfile(full_path):
            log.warn('File gone: %s'%meta['file_path'])
            kill_list.append(note_id)
            continue
        file_md5 = hashlib.md5(open(full_path).read()).hexdigest()
        if file_md5 != meta['md5']:
            log.info('Local file changed: %s'%meta['file_path'])
            local_changes.append(note_id)
    for killed in kill_list:
        store.remove(killed)
    return local_changes

def main():
    store = MetaStore()
    local_changes = get_local_changed(store)
    remote_changes = get_couch_changed(store)
    #remote_changes = get_couch_new(store)
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

    #download_notes(download, store)
    store.save()

if __name__ == '__main__':
    main()
