from model import CouchNote
import os
import pickle
import hashlib
import logging
log = logging.getLogger(__name__)

class MetaStore(object):

    def __init__(self, notes_root='./test_notes', store_path='meta.pickle'):
        self.store = {}
        self.store_path = store_path
        self.notes_root = notes_root
        if os.path.isfile(store_path):
            self.store = pickle.load(open(store_path))

    def __del__(self):
        log.debug('fart')
    def save(self):
        pickle.dump(self.store, open(self.store_path,'w'))

    def ids(self):
        return self.store.keys()

    def paths(self):
        return [self.store[key]['path'] for key in self.store]

    def path_mtime_md5s(self):
        return [(self.store[key]['path'], self.store[key]['md5'],
                            self.store[key]['mtime']) for key in self.store]

    def remove(self, note_id):
        # delete note
        #os.remove(os.path.join(self.notes_root,
        #                       self.store[note_id]['file_path']))
        del self.store[note_id]
        
    def get_meta(self, note_id):
        return self.store[note_id]

    def update_meta(self, note, file_path):
        self.update_metas(self, (note, file_path))

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
            self.store[meta['id']] = meta
