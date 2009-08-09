from couchdb import schema
from datetime import datetime

class CouchNote(schema.Document):
    summary = schema.TextField()
    detail = schema.TextField()
    file_path = schema.TextField()
    last_update_time = schema.DateTimeField(default=datetime.now)
    #udpate_notes = TextField() # going to tai chi, more of a status message?
    implements = schema.DictField(
        schema.Schema.build(couchnote = schema.BooleanField(default = True)))
