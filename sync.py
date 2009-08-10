#!/usr/bin/env python

import sys
import couchdb
from manager import NoteManager
from optparse import OptionParser

import logging
log = logging.getLogger(__name__)

def main():
    # Do option parsing
    usage = '''usage: %prog command [options]
    
Commands:
  import - imports unkown txt files as new couch notes
  sync - syncs non-conflicting changes with couch
  download - downloads all couch notes'''
    parser = OptionParser(usage=usage)
    parser.set_defaults(level=logging.WARN)
    parser.add_option('-d', '--debug', action='store_const', dest='level',
                      const=logging.DEBUG, help='Output DEBUG')
    parser.add_option('-v', '--verbose', action='store_const', dest='level',
                      const=logging.INFO, help='Output INFO')
    parser.add_option('-q', '--quite', action='store_const', dest='level',
                      const=logging.ERROR, help='Output ERROR')
    options, args = parser.parse_args(sys.argv)
    if len(args) < 2:
        parser.print_help()
        sys.exit('No command specified specified')

    # Setup logging output
    logging.basicConfig(level=options.level)
    log.debug('Getting underway')

    # Setup main objects
    # Better to pass as string to manager?
    server = couchdb.Server('http://localhost:5984/')
    db = server['noteish']
    note_man = NoteManager('./test_notes','meta.cache',db)

    # Main command processing
    if args[1] == 'sync':
        local_changes = note_man.get_local_changed()
        remote_changes = note_man.get_couch_changed()
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
        note_man.download_notes(download)
        note_man.upload_notes(upload)
        for conflict in conflicts:
            meta = note_man._cache[conflict]
            log.warn('Conflicting changes to: %(file_path)s [%(id)s]'%meta)
    elif args[1] == 'import':
        new_files = note_man.get_local_new()
        note_man.import_files(new_files)
    elif args[1] == 'download':
        # Check if anything was deleted
        note_man.get_local_changed()
        new_notes = note_man.get_couch_new()
        note_man.download_notes(new_notes)
    else:
        parser.print_help()
        sys.exit('Bad command: %s'%args[1])

    # Cleanup
    note_man._cache_save()

if __name__ == '__main__':
    main()
