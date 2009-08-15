import os
import hashlib
import pickle
from couchdb import schema
from datetime import datetime
import logging
log = logging.getLogger(__name__)

import cStringIO
from ConfigParser import RawConfigParser

class CouchNote(schema.Document):
    summary = schema.TextField()
    detail = schema.TextField()
    file_path = schema.TextField()
    last_update_time = schema.DateTimeField(default=datetime.now)
    #udpate_notes = TextField() # going to tai chi, more of a status message?
    implements = schema.DictField(
        schema.Schema.build(couchnote = schema.BooleanField(default = True)))

class NoteManager(object):
    '''Manages meta data linking couchnote objects to physical files.
    '''
    def __init__(self, notes_root, cache_path, db, dry_run=False):
        self._cache_path = cache_path
        self._notes_root = notes_root
        self._dry_run = dry_run
        self._db = db
        self._cache = {}
        self._cache_load()

    def _cache_load(self):
        if os.path.isfile(self._cache_path):
            self._cache = pickle.load(open(self._cache_path))

    def _cache_save(self):
        if not self._dry_run:
            pickle.dump(self._cache, open(self._cache_path,'w'))

    def update_metas(self, note_path_seq):
        for note, file_path in note_path_seq:
            full_path = os.path.join(self._notes_root,file_path)
            # Sanity check
            md5 = hashlib.md5(open(full_path).read()).hexdigest()
            if md5 != hashlib.md5(note.detail).hexdigest():
                raise ValueError, 'MD5 of file and note do not match'
            # make meta and save it
            meta = {}
            # id is immutable in couch so index<->attr can't drift
            meta['id'] = note.id
            meta['rev'] = note.rev
            meta['summary'] = note.summary
            meta['md5'] = md5
            meta['file_path'] = file_path
            meta['mtime'] = os.stat(os.path.join(self._notes_root,file_path))
            self._cache[meta['id']] = meta

    def upload_notes(self, note_ids):
        note_paths = []
        for note_id in note_ids:
            meta = self._cache[note_id]
            log.info('Pushing changes in note: %s'%meta['file_path'])
            note = CouchNote.load(self._db, meta['id'])
            note.detail = open(os.path.join(self._notes_root, meta['file_path'])).read()
            note.summary = meta['summary']
            if not self._dry_run:
                note.store(self._db)
            note_paths.append((note, meta['file_path']))
        self.update_metas(note_paths)

    def import_files(self, file_paths):
        note_paths = []
        for file_path in file_paths:
            log.info('Importing file: %s'%file_path)
            file_name = os.path.split(file_path)[1]
            summary = os.path.splitext(file_name)[0]
            detail = open(os.path.join(self._notes_root, file_path)).read()
            try:
                note = CouchNote(summary=summary, detail=detail,
                                 file_path=file_path)
                if not self._dry_run:
                    note.store(self._db)
                note_paths.append((note, file_path))
            except UnicodeDecodeError:
                log.error('Could not import text from file: %s'%file_path)
        self.update_metas(note_paths)

    def download_notes(self, ids):
        note_paths = []
        for note_id in ids:
            # Get note_id from view
            log.info('Downloading id: %s'%note_id)
            note = CouchNote.load(self._db, note_id)
            log.debug('Note: %s'%note)
            full_path = os.path.join(self._notes_root, note.file_path)
            if not os.path.isfile(full_path):
                file_dir = os.path.split(full_path)[0]
                if file_dir != '' and not os.path.isdir(file_dir):
                    log.info('Making dir: %s'%file_dir)
                    if not self._dry_run:
                        os.makedirs(file_dir)
                log.info('Creating file: %s'%note.file_path)
            if not self._dry_run:
                open(os.path.join(self._notes_root, note.file_path),'w').write(note.detail)
                note_paths.append((note, note.file_path))
        self.update_metas(note_paths)

    def get_local_new(self):
        local_new = []
        known_paths = [self._cache[key]['file_path'] for key in self._cache]
        for root, dirs, files in os.walk(self._notes_root):
            log.debug('Scanning %s'%root)
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext == '.txt':
                    full_path = os.path.join(root,file)
                    rel_path = full_path[len(self._notes_root):].lstrip('/')
                    if not rel_path in known_paths:
                        local_new.append(rel_path)
                        log.info('Unknown local file found: %s'%rel_path)
        return local_new

    def get_couch_new(self):
        remote_changes = []
        for row in self._db.view('couchnote/summaries'):
            if row['id'] not in self._cache:
                remote_changes.append(row['id'])
        return remote_changes

    def get_couch_changed(self, ids=None):
        if ids is None:
            ids = self._cache.keys()
        remote_changes = []
        for row in self._db.view('_all_docs', keys=ids):
            meta = self._cache[row['id']]
            if meta['rev'] != row['value']['rev']:
                log.info('Linked Couch Document changed: %s'%meta['file_path'])
                remote_changes.append(row['id'])
        return remote_changes

    def get_local_changed(self):
        local_changes = []
        kill_list = []
        for note_id, meta in self._cache.iteritems():
            full_path = os.path.join(self._notes_root,meta['file_path'])
            if not os.path.isfile(full_path):
                log.warn('File gone: %s'%meta['file_path'])
                kill_list.append(note_id)
                continue
            file_md5 = hashlib.md5(open(full_path).read()).hexdigest()
            if file_md5 != meta['md5']:
                log.info('Local file changed: %s'%meta['file_path'])
                local_changes.append(note_id)
        for killed in kill_list:
            del self._cache[killed]
        return local_changes

    def export_meta(self, id):
        meta = self._cache[id]
        cfg = RawConfigParser()
        cfg.add_section('couchdb')
        cfg.set('couchdb', 'id', id)
        cfg.set('couchdb', 'rev', meta['rev'])
        cfg.add_section('local')
        cfg.set('local', 'md5', meta['md5'])
        cfg.set('local', 'mtime', meta['mtime'])
        cfg.add_section('user')
        cfg.set('user', 'summary', meta['summary'])
        ret = cStringIO.StringIO()
        cfg.write(ret)
        return ret.getvalue()

    def import_meta(self, note_id, str):
        log.debug('Checking meta update for %s'%note_id)
        cfg_file = cStringIO.StringIO(str)
        cfg = RawConfigParser()
        cfg.readfp(cfg_file)
        summary = cfg.get('user', 'summary')
        if summary is not None:
            if summary != self._cache[note_id]['summary']:
                log.info('Summary updated on %s'%note_id)
                self._cache[note_id]['summary'] = summary
                self.upload_notes([note_id])

    def paths_to_ids(self, paths):
        ids = []
        clean_paths = []
        for path in paths:
            if path.startswith(self._notes_root):
                path = path[len(self._notes_root):]
            clean_paths.append(path)
        for note_id in self._cache:
            if self._cache[note_id]['file_path'] in clean_paths:
                ids.append(note_id)
        return ids
