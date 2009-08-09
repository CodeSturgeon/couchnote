#!/usr/bin/env python

import os
import sys
import couchdb
server = couchdb.Server('http://localhost:5984/')
db = server['noteish']

import hashlib

from store import MetaStore
from model import CouchNote

from optparse import OptionParser

import logging
log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

scan_dir = './test_notes'

def upload_notes(note_ids, store):
    updates = []
    for note_id in note_ids:
        meta = store[note_id]
        log.info('Updating note: %s'%meta['file_path'])
        note = CouchNote.load(db, meta['id'])
        note.detail = open(os.path.join(scan_dir, meta['file_path'])).read()
        note.store(db)
        updates.append((note, meta['file_path']))
    store.update_metas(updates)

def new_note(file_path, store):
    file_name = os.path.split(file_path)[1]
    summary = os.path.splitext(file_name)[0]
    detail = open().read()
    note = CouchNote(summary=summary, detail=detail)
    note.store(db)
    store.update_metas((note, file_path))

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
    for row in db.view('couchnote/paths'):
        if row['id'] not in store:
            remote_changes.append(row['id'])
    return remote_changes

def get_couch_changed(store):
    remote_changes = []
    for row in db.view('_all_docs', keys=store.keys()):
        meta = store[row['id']]
        if meta['rev'] != row['value']['rev']:
            log.info('Linked Couch Document changed: %s'%meta['file_path'])
            remote_changes.append(row['id'])
    return remote_changes

def get_local_changed(store):
    local_changes = []
    kill_list = []
    for note_id, meta in store.iteritems():
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
        del store[killed]
    return local_changes

def do_parser():
    usage = '''usage: %prog command [options]
    
Commands:
  import - imports unkown txt files as new couch notes
  sync - syncs non-conflicting changes with couch
  download - downloads all couch notes'''
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='store', dest='level',
                      help='Output INFO')
    options, args = parser.parse_args(sys.argv)
    if len(args) < 2:
        parser.print_help()
        sys.exit('No command specified specified')
    if args[1] not in ['import', 'sync', 'download']:
        parser.print_help()
        sys.exit('Bad command: %s'%args[1])
    return options, args

def main():
    options, args = do_parser()
    store = MetaStore()
    if args[1] == 'sync':
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

        if 0:
            print 'Uploading: %s'%upload
            print 'Downloading: %s'%download
            print 'Conlifting: %s'%conflicts

        download_notes(download, store)
        upload_notes(upload, store)
        for conflict in conflicts:
            meta = store[conflict]
            log.warn('Conflicting changes to: %(file_path)s [%(id)s]'%meta)
    store.save()

if __name__ == '__main__':
    main()
