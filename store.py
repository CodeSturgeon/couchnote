from model import CouchNote
import os
import pickle
import hashlib
import logging
log = logging.getLogger(__name__)

class MetaStore(dict):

    def __init__(self, notes_root='./test_notes', store_path='meta.pickle'):
        self.store_path = store_path
        self.notes_root = notes_root
        self.load()

    def load(self):
        if os.path.isfile(self.store_path):
            self.update(pickle.load(open(self.store_path)))

    #def __del__(self):
    #    self.save()

    def save(self):
        pickle.dump(self, open(self.store_path,'w'))

    def update_metas(self, note_path_seq):
        for note, file_path in note_path_seq:
            full_path = os.path.join(self.notes_root,file_path)
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
            meta['mtime'] = os.stat(os.path.join(self.notes_root,file_path))
            self[meta['id']] = meta
