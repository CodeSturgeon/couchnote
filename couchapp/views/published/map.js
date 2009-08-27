function(doc){
    if(doc.implements && doc.implements.published){
        emit(doc.summary, null);
    }
}
