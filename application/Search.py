from .Program import elasticsearch

def add_to_index(index, model):
    if not elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    elasticsearch.index(index=index, id=model.id, body=payload)

def remove_from_index(index, model):
    if not elasticsearch:
        return
    elasticsearch.delete(index=index, id=model.id)

def query_index(index, query, page, per_page):
	if not elasticsearch:
		return [], 0
	if( query == ""):
		search = elasticsearch.search(
			index=index,
			body={
				"sort" : {
					"rank":"asc"
				},
				"query" : {
					"term":{"verified" : "1"}
				},
				"from":(page-1)*per_page,
				"size":per_page
			})
	elif(query == "New"):
		search = elasticsearch.search(
			index=index,
			body={
				"sort" : {
					"newTime":"desc"
				},
				"query" : {
					"term":{"verified" : "1"}
				},
				"from":(page-1)*per_page,
				"size":per_page
			})
	else:
		search = elasticsearch.search(
			index=index,
			body={
				"query":{
					"bool":{
						"must":{
							"multi_match":{
								"query":query,
								"type":"most_fields",
								"fields":['name^3','plugins','datapacks','mods','tags^2','displayVersion^3','country']
							}
						},
						"filter":{
							"term":{
								"verified":"1"
							}
						}
					}
				},
				"from":(page-1)*per_page,
				"size":per_page
			})
	ids = [int(hit['_id']) for hit in search['hits']['hits']]
	return ids, search['hits']['total']['value']