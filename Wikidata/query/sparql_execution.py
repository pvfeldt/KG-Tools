import requests

# results->json
def split_answers(results):
    answers=[]
    if "results" in results:
        keys = results["head"]["vars"]
        for item in results["results"]["bindings"]:
            for key in keys:
                answer = item[key]["value"]
                if "call" not in key:
                    answer = answer.replace("http://www.wikidata.org/entity/", "")
                    answer = answer.replace("_", " ")
                answers.append(answer)
    elif "boolean" in results:
        answers.append(results["boolean"])
    return answers

def execute_query(sparql):
    endpoint_url = "https://query.wikidata.org/sparql"
    headers = {'User-Agent': 'agent'}

    input = {
        'query': sparql,
        'format': 'json'
    }
    answers=[]
    try:
        r = requests.get(endpoint_url, params=input, headers=headers, timeout=30,verify=False)
        results = r.json()
        answers=split_answers(results)
    except Exception as e:
        print(f"Other Error: {e}")
    return answers

# get the label of entities or relations
def get_label(entity_id):
    # might be literal
    if "Q" not in entity_id and "P" not in entity_id:
        return entity_id
    sparql = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    SELECT ?x WHERE {
        wd:"""+entity_id+""" rdfs:label ?x.
        FILTER(LANG(?x) = \"en\")
        }"""
    answer = execute_query(sparql)
    if answer==[]:
        return None
    else:
        return answer[0]

def execute_query_with_label(sparql):
    answer_dict={}
    answer_ids = execute_query(sparql)
    for id in answer_ids:
        answer_label=None
        while answer_label==None:
            answer_label=get_label(id)
        answer_dict[id] = answer_label
    return answer_dict

# get the id of entities or relations (may be multiple ids)
def get_id(entity_label):
    sparql="""
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?entity WHERE {
        ?entity rdfs:label \""""+entity_label+"""\"@en.
        }"""
    answer = execute_query(sparql)
    return answer

# search for (?,e), return relation labels
def get_in_relations(entity_id):
    relation_dict={}
    sparql = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT (?x0 AS ?value) WHERE {
        ?x1 ?x0 wd:"""+entity_id+""".
        FILTER regex(str(?x0), \"http://www.wikidata.org/\")
        }"""
    relation_ids = execute_query(sparql)
    relation_ids = list(set(relation_ids))
    for rel_id in relation_ids:
        rel_id=rel_id.split("/")[-1]
        rel_label=get_label(rel_id)
        relation_dict[rel_id]=rel_label
    return relation_dict

# search for (e,?), return relation labels
def get_out_relations(entity_id):
    relation_dict = {}
    sparql = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT (?x0 AS ?value) WHERE {
        wd:"""+entity_id+""" ?x0 ?x1.
        FILTER regex(str(?x0), \"http://www.wikidata.org/\")
        }"""
    relation_ids = execute_query(sparql)
    relation_ids = list(set(relation_ids))
    for rel_id in relation_ids:
        rel_id=rel_id.split("/")[-1]
        rel_label=get_label(rel_id)
        relation_dict[rel_id]=rel_label
    return relation_dict

# search for (?,r,e), return relation labels
def get_in_entities(entity_id,relation_id):
    entity_dict={}
    sparql = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    SELECT (?x1 AS ?value) WHERE {
        ?x1 wdt:"""+relation_id+""" wd:"""+entity_id+""".
        }"""
    entity_ids = execute_query(sparql)
    entity_ids = list(set(entity_ids))
    for ent_id in entity_ids:
        ent_id=ent_id.split("/")[-1]
        ent_label=get_label(ent_id)
        entity_dict[ent_id]=ent_label
    return entity_dict

# search for (e,r,?), return relation labels
def get_out_entities(entity_id,relation_id):
    entity_dict={}
    sparql = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    SELECT (?x1 AS ?value) WHERE {
        wd:"""+entity_id+""" wdt:"""+relation_id+""" ?x1.
        }"""
    entity_ids = execute_query(sparql)
    entity_ids = list(set(entity_ids))
    for ent_id in entity_ids:
        ent_id=ent_id.split("/")[-1]
        ent_label=get_label(ent_id)
        entity_dict[ent_id]=ent_label
    return entity_dict

def map_freebase_to_wikidata(entity_id):
    # input entity "m.xxx"
    entity_id=entity_id.replace("m.","/m/")
    entity_id=entity_id.replace("g.","/g/")
    entity_dict={}
    sparql="""
    SELECT ?item WHERE {
        ?item p:P646 ?statement.
        ?statement ps:P646 \""""+entity_id+"""\".
        SERVICE wikibase:label { 
            bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
            }
        }
    """
    entity_ids = execute_query(sparql)
    for ent_id in entity_ids:
        ent_id=ent_id.split("/")[-1]
        ent_label=get_label(ent_id)
        entity_dict[ent_id]=ent_label
    return entity_dict

def map_wikidata_to_freebase(entity_id):
    # input entity "m.xxx"
    sparql="""
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX ps: <http://www.wikidata.org/prop/statement/>
    PREFIX pq: <http://www.wikidata.org/prop/qualifier/>

    SELECT ?freebase_id WHERE {
        wd:"""+entity_id+""" p:P646 ?statement.
        ?statement ps:P646 ?freebase_id.
        }
    """
    entity_ids = execute_query(sparql)
    entity_id=entity_ids[0]
    entity_id=entity_id.replace("/m/","m.")
    entity_id=entity_id.replace("/g/","g.")

    return entity_id