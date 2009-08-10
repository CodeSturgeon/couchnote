#!/usr/bin/env python

import sys
import couchdb
from manager import NoteManager
from optparse import OptionParser, OptionGroup

import logging
log = logging.getLogger(__name__)

def main():
    # Do option parsing
    usage = '''usage: %prog command [options]
    
Commands:
  import - imports unknown txt files as new couch notes
  sync - syncs non-conflicting changes with couch
  download - downloads all couch notes'''
    parser = OptionParser(usage=usage,epilog=' ')
    parser.set_defaults(level=logging.WARN,
                        server_url='http://localhost:5984/',
                        database_name='noteish',
                        notes_root='./test_notes',
                        cache_path='meta.cache'
                       )

    couch_group = OptionGroup(parser, "CouchDB Options",
                              "Define connction to couchdb")
    couch_group.add_option('-s', '--server-url', action='store',
                           dest='server_url',
                           help='URL of the couchdb server')
    couch_group.add_option('-d', '--database-name', action='store',
                           dest='database_name',
                           help='Name of the couchdb')
    parser.add_option_group(couch_group)

    paths_group = OptionGroup(parser, "Path Options",
                              "Define local paths to be used by manager")
    paths_group.add_option('-n', '--note-root', action='store',
                           dest='notes_root',
                           help='Root path of the managed notes')
    paths_group.add_option('-c', '--cache-path', action='store',
                           dest='cache_path',
                           help='Path to cache storage file')
    parser.add_option_group(paths_group)

    output_group = OptionGroup(parser, "Output Options",
                                "Controll how much or little you are told")
    output_group.add_option('-V', '--debug', action='store_const',
                            dest='level', const=logging.DEBUG,
                            help='Output all messages')
    output_group.add_option('-v', '--verbose', action='store_const',
                            dest='level', const=logging.INFO,
                            help='Output INFO, WARN and ERROR messages')
    output_group.add_option('-q', '--quite', action='store_const',
                            dest='level', const=logging.ERROR,
                            help='Output only ERROR messages')
    parser.add_option_group(output_group)

    options, args = parser.parse_args(sys.argv)
    if len(args) < 2:
        parser.print_help()
        sys.exit('!!No command specified specified!!')

    # Setup logging output
    logging.basicConfig(level=options.level)
    log.debug('Getting underway')

    # Setup main objects
    # Better to pass as string to manager?
    server = couchdb.Server(options.server_url)
    db = server[options.database_name]
    note_man = NoteManager(notes_root=options.notes_root, db=db,
                           cache_path=options.cache_path)

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
        sys.exit('!!Bad command: %s!!'%args[1])

    # Cleanup
    note_man._cache_save()

if __name__ == '__main__':
    main()
