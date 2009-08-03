function(doc){
    if(doc.implements && doc.implements.couchnote){
        emit(doc.summary, null);
    }
}
