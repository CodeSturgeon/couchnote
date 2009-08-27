function(doc){
    if(doc.implements && doc.implements.published){
        last_publish = doc.published_versions.pop()['time'];
        emit(doc.summary, last_publish);
    }
}
