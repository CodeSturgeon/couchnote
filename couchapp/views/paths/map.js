function(doc){
    if(doc.implements && doc.implements.couchnote){
        emit(doc.file_path, doc._rev);
    }
}
