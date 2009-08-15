#!/usr/bin/env python

import os
import sys
import couchdb
from couchdb.client import ResourceNotFound
from manager import NoteManager
from optparse import OptionParser, OptionGroup

from tempfile import NamedTemporaryFile
from subprocess import call

import socket

import logging
log = logging.getLogger(__name__)

def main():
    defaults = {
            'level': logging.WARN,
            'server_url': 'http://localhost:5984/',
            'database_name': 'noteish',
            'notes_root': '~/Documents/Notes',
            'cache_path': '~/.couchnote.cache',
            'dry_run': False
        }

    if sys.argv[0].endswith('.py'):
        # Assume we are in dev mode and change defaults
        defaults.update({
                'database_name': 'notetest',
                'notes_root': './test_notes',
                'cache_path': './meta.cache'
            })

    # Do option parsing
    usage = '''usage: %prog command [options]
    
Commands:
  import - imports unknown txt files as new couch notes
  sync - syncs non-conflicting changes with couch
  download - downloads all couch notes'''
    parser = OptionParser(usage=usage,epilog=' ')
    parser.set_defaults(**defaults)

    parser.add_option('-n', '--dry-run', action='store_true',
                           dest='dry_run',
                           help='Make no actual changes')

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
    paths_group.add_option('-r', '--note-root', action='store',
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
    log.debug('Options %s'%options)

    # Setup main objects
    server = couchdb.Server(options.server_url)
    try:
        db = server[options.database_name]
    except socket.error:
        sys.exit('Could not connect to %s'%options.server_url)
    except ResourceNotFound:
        sys.exit('Could not find db named "%s"'%options.database_name)
    notes_root = os.path.expanduser(options.notes_root)
    cache_path = os.path.expanduser(options.cache_path)
    note_man = NoteManager(notes_root=notes_root, db=db,
                           cache_path=cache_path, dry_run = options.dry_run)

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
    elif args[1] == 'medit':
        if len(args) < 3:
            sys.exit('Need to specify a path!')
        elif len(args) > 3:
            log.warn('Discarding: %s'%args[3:])
        note_id = note_man.paths_to_ids(args[2:3])[0]
        cfg_str = note_man.export_meta(note_id)
        tmp_file = NamedTemporaryFile()
        tmp_file.write(cfg_str)
        tmp_file.flush()
        editor = os.getenv('EDITOR')
        if call([editor,tmp_file.name]) != 0:
            sys.exit('Editor problem')
        note_man.import_meta(note_id, open(tmp_file.name).read())
        tmp_file.close()
    else:
        parser.print_help()
        sys.exit('!!Bad command: %s!!'%args[1])

    # Cleanup
    note_man._cache_save()

if __name__ == '__main__':
    main()
