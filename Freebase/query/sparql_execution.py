import os
import sys
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from collections import defaultdict
from typing import List, Tuple
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import urllib
from pathlib import Path
from tqdm import tqdm

ELQ_SERVICE_URL = "http://localhost:5688/entity_linking"
FREEBASE_SPARQL_WRAPPER_URL = "http://localhost:8890/sparql"
FREEBASE_ODBC_PORT = "13001"
sparql = SPARQLWrapper(FREEBASE_SPARQL_WRAPPER_URL)
sparql.setReturnFormat(JSON)

path = str(Path(__file__).parent.absolute())

with open(path + '/../ontology/fb_roles', 'r') as f:
    contents = f.readlines()

roles = set()
for line in contents:
    fields = line.split()
    roles.add(fields[1])

# connection for freebase
odbc_conn = None
def initialize_odbc_connection():
    global odbc_conn
    odbc_conn = pyodbc.connect(
        f'DRIVER={path}/../lib/virtodbc.so;Host=localhost:{FREEBASE_ODBC_PORT};UID=dba;PWD=dba'
    )
    odbc_conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf8')
    odbc_conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf8')
    odbc_conn.setencoding(encoding='utf8')
    odbc_conn.timeout = 1
    print('Freebase Virtuoso ODBC connected')


def execute_query(query: str) -> List[str]:
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()
    except urllib.error.URLError:
        print(query)
        # exit(0)
    rtn = []
    for result in results['results']['bindings']:
        assert len(result) == 1  # only select one variable
        for var in result:
            rtn.append(result[var]['value'].replace('http://rdf.freebase.com/ns/', '').replace("-08:00", ''))

    return rtn

def execute_query_with_odbc(query:str) -> List[str]:
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    # print('successfully connnected to Freebase ODBC')
    result_set = set()
    query2 = "SPARQL " + query
    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query2)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
            for row in rows:
                result_set.add(row[0])
    except Exception as e:
        print("error:",e)
        pass
        # print(f"Query Execution Failed:{query2}")
        # exit(0)
    
    # for row in rows:
    #     result_set.add(row[0])
    return result_set


def get_types_with_odbc(entity: str) -> List[str]:

    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    
    types = set()

    query = ("""SPARQL
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://rdf.freebase.com/ns/> 
    SELECT (?x0 AS ?value) WHERE {
    SELECT DISTINCT ?x0  WHERE {
    """
             ':' + entity + ' :type.object.type ?x0 . '
                            """
    }
    }
    """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query1}")
        rows=[]
        # exit(0)
    

    for row in rows:
        types.add(row[0].replace('http://rdf.freebase.com/ns/', ''))
    
    if len(types)==0:
        return []
    else:
        return list(types)

def get_in_relations_with_odbc(entity: str):
    in_relations = set()

    query1 = ("""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX : <http://rdf.freebase.com/ns/> 
            SELECT (?x0 AS ?value) WHERE {
            SELECT DISTINCT ?x0  WHERE {
            """
              '?x1 ?x0 ' + ':' + entity + '. '
                                          """
     FILTER regex(?x0, "http://rdf.freebase.com/ns/")
     }
     }
     """)
    # print(query1)

    sparql.setQuery(query1)
    try:
        results = sparql.query().convert()
    except urllib.error.URLError:
        print(query1)
        # exit(0)
    for result in results['results']['bindings']:
        in_relations.add(result['value']['value'].replace('http://rdf.freebase.com/ns/', ''))

    return in_relations


def get_out_relations_with_odbc(entity: str):
    out_relations = set()

    query2 = ("""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX : <http://rdf.freebase.com/ns/> 
        SELECT (?x0 AS ?value) WHERE {
        SELECT DISTINCT ?x0  WHERE {
        """
              ':' + entity + ' ?x0 ?x1 . '
                             """
    FILTER regex(?x0, "http://rdf.freebase.com/ns/")
    }
    }
    """)
    # print(query2)

    sparql.setQuery(query2)
    try:
        results = sparql.query().convert()
    except urllib.error.URLError:
        print(query2)
        # exit(0)
    for result in results['results']['bindings']:
        out_relations.add(result['value']['value'].replace('http://rdf.freebase.com/ns/', ''))

    return out_relations
    

def query_two_hop_relations_gmt(entities_path, output_file):
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    res_dict = defaultdict(list)
    entities = load_json(entities_path)
    for entity in tqdm(entities, total=len(entities)):
        query = """
        SPARQL SELECT DISTINCT ?x0 as ?r0 ?y as ?r1 where {{
            {{ ?x1 ?x0 {} . ?x2 ?y ?x1 }}
            UNION
            {{ ?x1 ?x0 {} . ?x1 ?y ?x2 }}
            UNION
            {{ {} ?x0 ?x1 . ?x2 ?y ?x1 }}
            UNION
            {{ {} ?x0 ?x1 . ?x1 ?y ?x2 }}
            FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
            FILTER (?y != rdf:type && ?y != rdfs:label)
            FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
            FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
            FILTER( !regex(?x0,"wikipedia","i"))
            FILTER( !regex(?y,"wikipedia","i"))
            FILTER( !regex(?x0,"type.object","i"))
            FILTER( !regex(?y,"type.object","i"))
            FILTER( !regex(?x0,"common.topic","i"))
            FILTER( !regex(?y,"common.topic","i"))
            FILTER( !regex(?x0,"_id","i"))
            FILTER( !regex(?y,"_id","i"))
            FILTER( !regex(?x0,"#type","i"))
            FILTER( !regex(?y,"#type","i"))
            FILTER( !regex(?x0,"#label","i"))
            FILTER( !regex(?y,"#label","i"))
            FILTER( !regex(?x0,"/ns/freebase","i"))
            FILTER( !regex(?y,"/ns/freebase","i"))
            FILTER( !regex(?x0, "ns/common."))
            FILTER( !regex(?y, "ns/common."))
            FILTER( !regex(?x0, "ns/type."))
            FILTER( !regex(?y, "ns/type."))
            FILTER( !regex(?x0, "ns/kg."))
            FILTER( !regex(?y, "ns/kg."))
            FILTER( !regex(?x0, "ns/user."))
            FILTER( !regex(?y, "ns/user."))
            FILTER( !regex(?x0, "ns/base."))
            FILTER( !regex(?y, "ns/base."))
            FILTER( !regex(?x0, "ns/dataworld."))
            FILTER( !regex(?y, "ns/dataworld."))
            FILTER regex(?x0, "http://rdf.freebase.com/ns/")
            FILTER regex(?y, "http://rdf.freebase.com/ns/")
        }} 
        
        LIMIT 300
        """.format('ns:'+entity, 'ns:'+entity, 'ns:'+entity, 'ns:'+entity)
        try:
            with odbc_conn.cursor() as cursor:
                cursor.execute(query)
                # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
            res = set()
            for row in rows:
                if row[0].startswith("http://rdf.freebase.com/ns/"):
                    res.add(row[0].replace('http://rdf.freebase.com/ns/', ''))
                if row[1].startswith("http://rdf.freebase.com/ns/"):
                    res.add(row[1].replace('http://rdf.freebase.com/ns/', ''))
            res_dict[entity] = list(res)
            
        except Exception:
            # print(f"Query Execution Failed:{query1}")
            rows=[]
    
    # return list(res)
    dump_json(res_dict, output_file)


def get_2hop_relations_with_odbc(entity: str):
    in_relations = set()
    out_relations = set()
    paths = []

    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()


    query1 = ("""SPARQL 
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/>
            SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
            """
              '?x1 ?x0 ' + 'ns:' + entity + '. '
                                          """
                ?x2 ?y ?x1 .
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"type.object","i"))
                  FILTER( !regex(?y,"type.object","i"))
                  FILTER( !regex(?x0,"common.topic","i"))
                  FILTER( !regex(?y,"common.topic","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/common."))
                  FILTER( !regex(?y, "ns/common."))
                  FILTER( !regex(?x0, "ns/type."))
                  FILTER( !regex(?y, "ns/type."))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/user."))
                  FILTER( !regex(?y, "ns/user."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)
    # print(query1)
    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query1)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query1}")
        rows=[]
        # exit(0)


    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        in_relations.add(r0)
        in_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0, r1))
        

    query2 = ("""SPARQL 
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/> 
            SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
            """
              '?x1 ?x0 ' + 'ns:' + entity + '. '
                                          """
                ?x1 ?y ?x2 .
                """
                  'FILTER (?x2 != ns:'+entity+' )'
                  """
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"type.object","i"))
                  FILTER( !regex(?y,"type.object","i"))
                  FILTER( !regex(?x0,"common.topic","i"))
                  FILTER( !regex(?y,"common.topic","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/common."))
                  FILTER( !regex(?y, "ns/common."))
                  FILTER( !regex(?x0, "ns/type."))
                  FILTER( !regex(?y, "ns/type."))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/user."))
                  FILTER( !regex(?y, "ns/user."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query2)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query2}")
        rows = []
        # exit(0)
    
    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        in_relations.add(r0)
        out_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0, r1 + '#R'))

    
    query3 = ("""SPARQL 
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX ns: <http://rdf.freebase.com/ns/>
                SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
                """
              'ns:' + entity + ' ?x0 ?x1 . '
                             """
                ?x2 ?y ?x1 .
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"type.object","i"))
                  FILTER( !regex(?y,"type.object","i"))
                  FILTER( !regex(?x0,"common.topic","i"))
                  FILTER( !regex(?y,"common.topic","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/common."))
                  FILTER( !regex(?y, "ns/common."))
                  FILTER( !regex(?x0, "ns/type."))
                  FILTER( !regex(?y, "ns/type."))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/user."))
                  FILTER( !regex(?y, "ns/user."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query3)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query3}")
        rows = []
        # exit(0)
    
    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        out_relations.add(r0)
        in_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0 + '#R', r1))


    query4 = ("""SPARQL 
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX ns: <http://rdf.freebase.com/ns/>
                SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
                """
              'ns:' + entity + ' ?x0 ?x1 . '
                             """
                ?x1 ?y ?x2 .
                """
                  'FILTER (?x2 != ns:'+entity+' )'
                """
                FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                FILTER (?y != rdf:type && ?y != rdfs:label)
                FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                FILTER( !regex(?x0,"wikipedia","i"))
                FILTER( !regex(?y,"wikipedia","i"))
                FILTER( !regex(?x0,"type.object","i"))
                FILTER( !regex(?y,"type.object","i"))
                FILTER( !regex(?x0,"common.topic","i"))
                FILTER( !regex(?y,"common.topic","i"))
                FILTER( !regex(?x0,"_id","i"))
                FILTER( !regex(?y,"_id","i"))
                FILTER( !regex(?x0,"#type","i"))
                FILTER( !regex(?y,"#type","i"))
                FILTER( !regex(?x0,"#label","i"))
                FILTER( !regex(?y,"#label","i"))
                FILTER( !regex(?x0,"/ns/freebase","i"))
                FILTER( !regex(?y,"/ns/freebase","i"))
                FILTER( !regex(?x0, "ns/common."))
                FILTER( !regex(?y, "ns/common."))
                FILTER( !regex(?x0, "ns/type."))
                FILTER( !regex(?y, "ns/type."))
                FILTER( !regex(?x0, "ns/kg."))
                FILTER( !regex(?y, "ns/kg."))
                FILTER( !regex(?x0, "ns/user."))
                FILTER( !regex(?y, "ns/user."))
                FILTER( !regex(?x0, "ns/dataworld."))
                FILTER( !regex(?y, "ns/dataworld."))
                FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                FILTER regex(?y, "http://rdf.freebase.com/ns/")
                }
                LIMIT 1000
                """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query4)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query4}")
        rows = []
        # exit(0)

    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        out_relations.add(r0)
        out_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0 + '#R', r1 + '#R'))

    return in_relations, out_relations, paths

def get_2hop_relations_with_odbc_wo_filter(entity: str):
    in_relations = set()
    out_relations = set()
    paths = []

    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()


    query1 = ("""SPARQL 
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/>
            SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
            """
              '?x1 ?x0 ' + 'ns:' + entity + '. '
                                          """
                ?x2 ?y ?x1 .
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)
    # print(query1)
    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query1)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query1}")
        rows=[]
        # exit(0)


    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        in_relations.add(r0)
        in_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0, r1))
        

    query2 = ("""SPARQL 
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/> 
            SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
            """
              '?x1 ?x0 ' + 'ns:' + entity + '. '
                                          """
                ?x1 ?y ?x2 .
                """
                  'FILTER (?x2 != ns:'+entity+' )'
                  """
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query2)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query2}")
        rows = []
        # exit(0)
    
    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        in_relations.add(r0)
        out_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0, r1 + '#R'))

    
    query3 = ("""SPARQL 
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX ns: <http://rdf.freebase.com/ns/>
                SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
                """
              'ns:' + entity + ' ?x0 ?x1 . '
                             """
                ?x2 ?y ?x1 .
                  FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                  FILTER (?y != rdf:type && ?y != rdfs:label)
                  FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                  FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                  FILTER( !regex(?x0,"wikipedia","i"))
                  FILTER( !regex(?y,"wikipedia","i"))
                  FILTER( !regex(?x0,"_id","i"))
                  FILTER( !regex(?y,"_id","i"))
                  FILTER( !regex(?x0,"#type","i"))
                  FILTER( !regex(?y,"#type","i"))
                  FILTER( !regex(?x0,"#label","i"))
                  FILTER( !regex(?y,"#label","i"))
                  FILTER( !regex(?x0,"/ns/freebase","i"))
                  FILTER( !regex(?y,"/ns/freebase","i"))
                  FILTER( !regex(?x0, "ns/kg."))
                  FILTER( !regex(?y, "ns/kg."))
                  FILTER( !regex(?x0, "ns/dataworld."))
                  FILTER( !regex(?y, "ns/dataworld."))
                  FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                  FILTER regex(?y, "http://rdf.freebase.com/ns/")
                  }
                  LIMIT 1000
                  """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query3)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query3}")
        rows = []
        # exit(0)
    
    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        out_relations.add(r0)
        in_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0 + '#R', r1))


    query4 = ("""SPARQL 
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX ns: <http://rdf.freebase.com/ns/>
                SELECT distinct ?x0 as ?r0 ?y as ?r1 WHERE {
                """
              'ns:' + entity + ' ?x0 ?x1 . '
                             """
                ?x1 ?y ?x2 .
                """
                  'FILTER (?x2 != ns:'+entity+' )'
                """
                FILTER (?x0 != rdf:type && ?x0 != rdfs:label)
                FILTER (?y != rdf:type && ?y != rdfs:label)
                FILTER(?x0 != ns:type.object.type && ?x0 != ns:type.object.instance)
                FILTER(?y != ns:type.object.type && ?y != ns:type.object.instance)
                FILTER( !regex(?x0,"wikipedia","i"))
                FILTER( !regex(?y,"wikipedia","i"))
                FILTER( !regex(?x0,"_id","i"))
                FILTER( !regex(?y,"_id","i"))
                FILTER( !regex(?x0,"#type","i"))
                FILTER( !regex(?y,"#type","i"))
                FILTER( !regex(?x0,"#label","i"))
                FILTER( !regex(?y,"#label","i"))
                FILTER( !regex(?x0,"/ns/freebase","i"))
                FILTER( !regex(?y,"/ns/freebase","i"))
                FILTER( !regex(?x0, "ns/kg."))
                FILTER( !regex(?y, "ns/kg."))
                FILTER( !regex(?x0, "ns/dataworld."))
                FILTER( !regex(?y, "ns/dataworld."))
                FILTER regex(?x0, "http://rdf.freebase.com/ns/")
                FILTER regex(?y, "http://rdf.freebase.com/ns/")
                }
                LIMIT 1000
                """)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query4)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query4}")
        rows = []
        # exit(0)

    for row in rows:
        r0 = row[0].replace('http://rdf.freebase.com/ns/', '')
        r1 = row[1].replace('http://rdf.freebase.com/ns/', '')
        out_relations.add(r0)
        out_relations.add(r1)

        if r0 in roles and r1 in roles:
            paths.append((r0 + '#R', r1 + '#R'))

    return in_relations, out_relations, paths


def get_label(entity: str) -> str:
    """Get the label of an entity in Freebase"""
    query = ("""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX : <http://rdf.freebase.com/ns/> 
        SELECT (?x0 AS ?label) WHERE {
        SELECT DISTINCT ?x0  WHERE {
        """
             ':' + entity + ' rdfs:label ?x0 . '
                            """
                            FILTER (langMatches( lang(?x0), "EN" ) )
                             }
                             }
                             """)
    # # print(query)
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()
    except urllib.error.URLError:
        print(query)
        # exit(0)
    rtn = []
    for result in results['results']['bindings']:
        label = result['label']['value']
        rtn.append(label)
    if len(rtn) != 0:
        return rtn[0]
    else:
        return None


import pyodbc
def pyodbc_test():
    conn = pyodbc.connect(f'DRIVER={path}/../lib/virtodbc.so;Host=localhost:{FREEBASE_ODBC_PORT};UID=dba;PWD=dba')
    print(conn)
    conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf8')
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf8')
    conn.setencoding(encoding='utf8')
    
    with conn.cursor() as cursor:
        cursor.execute("SPARQL SELECT ?subject ?object WHERE { ?subject rdfs:subClassOf ?object }")
        # rows = cursor.fetchall()
        rows = cursor.fetchmany(10000)
    
    for row in rows:
        row = str(row)
        print(row)
    conn.commit()
    conn.close()


def get_label_with_odbc(entity: str) -> str:
    """Get the label of an entity in Freebase"""

    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
        
    query = ("""SPARQL
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ns: <http://rdf.freebase.com/ns/> 
        SELECT (?x0 AS ?label) WHERE {
        SELECT DISTINCT ?x0  WHERE {
        """
             'ns:' + entity + ' rdfs:label ?x0 . '
                            """
                            FILTER (langMatches( lang(?x0), "EN" ) )
                             }
                             }
                             """)

    # query = query.replace("\n"," ")
    # print(query)
    rows=[]
    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query}")
        # exit(0)
        pass
    
    
    rtn = []
    for row in rows:
        # print(type(row))
        rtn.append(row[0])
    
    if len(rtn) != 0:
        return rtn[0]
    else:
        return None

def get_1hop_relations_with_odbc(entity):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    
    relations = set()

    query = ("""SPARQL
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX : <http://rdf.freebase.com/ns/> 
            SELECT (?x0 AS ?value) WHERE {
            SELECT DISTINCT ?x0  WHERE {
            """
              '{ ?x1 ?x0 ' + ':' + entity + ' }'
              + ' UNION '
              + '{ :' + entity + ' ?x0 ?x1 ' + '}'
                                          """
     FILTER regex(?x0, "http://rdf.freebase.com/ns/")
     }
     }
     """)


    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query}")
        # exit(0)
        pass
    

    for row in rows:
        relations.add(row[0].replace('http://rdf.freebase.com/ns/', ''))

    return relations


def get_freebase_mid_from_wikiID(wikiID: int):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    
    mid = set()

    query2 = ("""SPARQL
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX : <http://rdf.freebase.com/ns/> 
        SELECT (?x0 AS ?value) WHERE {
        SELECT DISTINCT ?x0  WHERE {
        """
              '?x0 <http://rdf.freebase.com/key/wikipedia.en_id> ' + f'"{wikiID}"'
                             """
    FILTER regex(?x0, "http://rdf.freebase.com/ns/")
    }
    }
    """)
    # print(query2)
    

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query2)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query2}")
        # exit(0)
        pass
    

    for row in rows:
        mid.add(row[0].replace('http://rdf.freebase.com/ns/', ''))
    
    if len(mid)==0:
        return ''
    else:
        return list(mid)[0]


def load_json(fname, mode="r", encoding="utf8"):
    if "b" in mode:
        encoding = None
    with open(fname, mode=mode, encoding=encoding) as f:
        return json.load(f)


def dump_json(obj, fname, indent=4, mode='w' ,encoding="utf8", ensure_ascii=False):
    if "b" in mode:
        encoding = None
    with open(fname, "w", encoding=encoding) as f:
        return json.dump(obj, f, indent=indent, ensure_ascii=ensure_ascii)


def get_entity_labels(src_path, tgt_path):
    entities_list = load_json(src_path)
    res = dict()
    # for entity in entities_list:
    for entity in tqdm(entities_list, total=len(entities_list),desc=f'Querying entity labels'):
        label = get_label_with_odbc(entity)
        res[entity] = label
    dump_json(res, tgt_path)


def query_relation_domain_range_label_odbc(input_path, output_path):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    relations = load_json(input_path)
    
    res_dict = dict()
    for relation in tqdm(relations):
        query = """
        SPARQL DESCRIBE {}
        """.format('ns:' + relation)
        
        try:
            with odbc_conn.cursor() as cursor:
                cursor.execute(query)
                # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
        except Exception:
            print(f"Query Execution Failed:{query}")
            # exit(0)
        
        res_dict[relation] = dict()
        for row in rows:
            if '#domain' in row[1]:
                res_dict[relation]["domain"] = row[2].replace('http://rdf.freebase.com/ns/', '')
            elif '#range' in row[1]:
                res_dict[relation]["range"] = row[2].replace('http://rdf.freebase.com/ns/', '')
            elif '#label' in row[1]:
                res_dict[relation]["label"] = row[2].replace('http://rdf.freebase.com/ns/', '')
    
    dump_json(res_dict, output_path)

def freebase_query_entity_type_with_odbc(entities_path, output_path):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    
    res_dict = defaultdict(list)
    entities = load_json(entities_path)
    count = 0
    for entity in entities:
        query = """
        SPARQL DESCRIBE {}
        """.format('ns:' + entity)
        print('count: {}'.format(count))
        count += 1
        
        try:
            with odbc_conn.cursor() as cursor:
                cursor.execute(query)
                # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
            for row in rows:
                if row[1] == 'http://rdf.freebase.com/ns/kg.object_profile.prominent_type':
                    if row[2].startswith('http://rdf.freebase.com/ns/'):
                        # res_dict[entity].append(row[2])
                        res_dict[entity].append(row[2].replace('http://rdf.freebase.com/ns/', ''))
        except Exception:
            # print(f"Query Execution Failed:{query1}")
            rows=[]
            # exit(0)
    
    dump_json(output_path, res_dict)

"""
copied from `relation_retrieval/sparql_executor.py`
"""

def get_freebase_relations_with_odbc(data_path, limit=100):
    """Get all relations of Freebase"""
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()
    # {{ }}: to escape
    if limit > 0:
        query = """
        SPARQL SELECT DISTINCT ?p (COUNT(?p) as ?freq) WHERE {{
            ?subject ?p ?object
        }}
        LIMIT {}
        """.format(limit)
    else:
        query = """
        SPARQL SELECT DISTINCT ?p (COUNT(?p) as ?freq) WHERE {{
            ?subject ?p ?object
        }}
        """
    print('query: {}'.format(query))
    
    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception:
        # print(f"Query Execution Failed:{query1}")
        rows=[]
        # exit(0)
    
    rtn = []
    for row in rows:
        rtn.append([row[0], int(row[1])])
    
    if len(rtn) != 0:
        dump_json(rtn, data_path)

def freebase_relations_post_process(input_path, output_path):
    input_data = load_json(input_path)
    print(f'input length: {len(input_data)}')
    output_data = [item[0] for item in input_data]
    output_data = [item for item in output_data if item.startswith("http://rdf.freebase.com/ns/")]
    output_data = [item.replace('http://rdf.freebase.com/ns/', '') for item in output_data]
    output_data = list(set(output_data))
    print(f'output length: {len(output_data)}')
    dump_json(output_data, output_path)

def get_in_entities_with_odbc(entity, relation):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()

    in_entities = set()

    # query1 = ("""SPARQL
    #         PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    #         PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    #         PREFIX : <http://rdf.freebase.com/ns/>
    #         SELECT DISTINCT ?x0  WHERE {
    #         """
    #           '?x0 ns:' + relation +" ns:"+ entity + '. '
    #                                        """
    #   FILTER regex(?x0, "http://rdf.freebase.com/ns/")
    #   }
    #   }
    #   """)
    query1=("""SPARQL
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/> 
            SELECT DISTINCT ?x0 WHERE {
                ?x0 ns:"""+relation+" ns:"+entity+ " .\n"+
            """
                FILTER regex(str(?x0), "^http://rdf.freebase.com/ns/")
            }
      """)
    # print(query1)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query1)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception as e:
        # print(f"Query Execution Failed:{query1}")
        print(e)
        exit(0)

    for row in rows:
        in_entities.add(row[0].replace('http://rdf.freebase.com/ns/', ''))
    in_entities = list(in_entities)
    return in_entities

def get_out_entities_with_odbc(entity, relation):
    # build connection
    global odbc_conn
    if odbc_conn == None:
        initialize_odbc_connection()

    out_entities = set()

    # query1 = ("""SPARQL
    #         PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    #         PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    #         PREFIX : <http://rdf.freebase.com/ns/>
    #         SELECT DISTINCT ?x0  WHERE {
    #         """
    #           '?x0 ns:' + relation +" ns:"+ entity + '. '
    #                                        """
    #   FILTER regex(?x0, "http://rdf.freebase.com/ns/")
    #   }
    #   }
    #   """)
    query1=("""SPARQL
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ns: <http://rdf.freebase.com/ns/> 
            SELECT DISTINCT ?x0 WHERE {
                ns:"""+entity+" ns:"+relation+ " ?x0 .\n"+
            """
                FILTER regex(str(?x0), "^http://rdf.freebase.com/ns/")
            }""")
    # print(query1)

    try:
        with odbc_conn.cursor() as cursor:
            cursor.execute(query1)
            # rows = cursor.fetchall()
            rows = cursor.fetchmany(10000)
    except Exception as e:
        # print(f"Query Execution Failed:{query1}")
        print(e)
        exit(0)

    for row in rows:
        out_entities.add(row[0].replace('http://rdf.freebase.com/ns/', ''))
    out_entities = list(out_entities)
    return out_entities
