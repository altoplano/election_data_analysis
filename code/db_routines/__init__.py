#!/usr/bin/python3
# under construction
# Creates a table with columns specified in arg3 file, assuming format from state arg1.
# arg 1: a two-letter state code
# arg 2: table_name
# arg 3: (a path to) a file containing metadata from that state

import sys
from pathlib import Path
import re
import psycopg2
from psycopg2 import sql
from datetime import datetime

import clean as cl
from munge_routines import get_upsert_id


    

# process info from state context_dictionary into db
# *** UNDER CONSTRUCTION
def context_to_cdf(s,con,cur):
    rs = [str(datetime.now())]
    cdf_field_datatype_d= {'type':'TEXT','enddate':'DATE','startdate':'DATE'}  # *** build this programmatically from CDF schema def file?
    state_rvd = {'fieldname':'name','datatype':'text','value':s.name}
    state_ovds = []
    [status,state_id] = get_upsert_id(s.schema_name,'reportingunit',state_rvd)
    if status == 'inserted':
        rs.append('WARNING: '+s.name+' was not in cdf.reportingunit, had to be inserted.')
    for k in ['election']:   # e.g., k ='election'
        for kk in s.context_dictionary[k].keys():   # e.g., kk='General Election 2018-11-06'
            req_var_d= {'fieldname':'name','datatype':'text','value':kk}
            other_var_ds = []
            ## list other fields in table
            for kkk in s.context_dictionary[k][kk].keys():  # e.g., kkk='Type'
                other_var_ds.append(  {'fieldname':kkk.lower(),'datatype':cdf_field_datatype_d[kkk.lower()],'value':s.context_dictionary[k][kk][kkk]})
        

            get_upsert_id(s.schema,k,req_var_d,other_var_ds,con,cur)
    return('</p><p>'.join(rs))


# the main event: process a datafile into the cdf schema
def raw_df_to_db(df,m,conn,cur,cdf_schema):
    rs = [str(datetime.now())]
    
    return('</p><p>'.join(rs))



def file_to_sql_statement_list(fpath):
    query_list = []
    with open(fpath,'r') as f:
        fstring = f.read()
    p = re.compile('-- .*$',re.MULTILINE)
    clean_string = re.sub(p,' ',fstring)            # get rid of comments
    clean_string = re.sub('\n|\r',' ',clean_string)    # get rid of newlines
    query_list = clean_string.split(';')
    query_list = [q.strip() for q in query_list]    # strip leading and trailing whitespace
    return(query_list)



    
def parse_line(s,line):
    '''parse_line takes a state and a line of (metadata) text and parses it, including changing the type in the file to the type required by psql, according to the state's type-map dictionary'''
    d=s.type_map
    p=s.meta_parser
    m = p.search(line)
    field = (m.group('field')).replace(' ','_')
    type = d[m.group('type')]
    number = m.group('number')
    if number:
        type=type+(number)
    try:
        comment = m.group('comment')
    except:
        comment = ''
    return(field,type,comment)

def create_table(df):
## clean the metadata file
    fpath = cl.extract_first_col_defs(df.state.path_to_state_dir+'meta/'+df.metafile_name,df.state.path_to_state_dir+'tmp/',df.metafile_encoding)
    create_query = 'CREATE TABLE {}.{} ('
    sql_ids_create = [df.state.schema_name,df.table_name]
    sql_ids_comment = []
    strs_create = []
    strs_comment = []
    comments = []
    var_defs = []
    with open(fpath,'r',encoding=df.metafile_encoding) as f:
        lines = f.readlines()
    for line in lines:
        if line.find('"')>0:
            print('create_table:Line has double quote, will not be processed:\n'+line)
        else:
            try:
                [field,type,comment] = parse_line(df.state,line)
            except:
                print('create_table:Quoted line cannot be parsed, will not be processed: \n"'+line+'"')
                [field,type,comment] = ['parse_error','parse_error','parse_error']
            if len(comment):
                comments.append('comment on column {}.{}.{} is %s;')
                sql_ids_comment += [df.state.schema_name,df.table_name,field]
                strs_comment.append(comment)
        ## check that type var is clean before inserting it
            p = re.compile('^[\w\d()]+$')       # type should contain only alphanumerics and parentheses
            if p.match(type):
                var_defs.append('{} '+ type)    # not safest way to pass the type, but not sure how else to do it ***
                sql_ids_create.append(field)
            else:
                var_defs.append('corrupted type')
    create_query = create_query + ','.join(var_defs) + ');' +  ' '.join(comments)

    return(create_query,strs_create+strs_comment,sql_ids_create+sql_ids_comment)
        
def load_data(conn,cursor,state,df):      ## does this belong in app.py? *** might not need psycopg2 here then
# write raw data to db
    ext = df.file_name.split('.')[-1]    # extension, determines format
    if ext == 'txt':
        q = "COPY {}.{} FROM STDIN DELIMITER E'\\t' QUOTE '\"' CSV HEADER"
    elif ext == 'csv':
        q = "COPY {}.{} FROM STDIN DELIMITER ',' CSV HEADER"

    
    clean_file=cl.remove_null_bytes(state.path_to_state_dir+'data/'+df.file_name,'local_data/tmp/')
    with open(clean_file,mode='r',encoding=df.encoding,errors='ignore') as f:
        cursor.copy_expert(sql.SQL(q).format(sql.Identifier(state.schema_name),sql.Identifier(df.table_name)),f)
    conn.commit()
# update values to obey convention *** need to take this out, but first make sure /analysis will work
    fup = []
    for field in df.value_convention.keys():
        condition = []
        for value in df.value_convention[field].keys():
            condition.append(" WHEN "+field+" = '"+value+"' THEN '"+df.value_convention[field][value]+"' ")
        fup.append(field + " =  CASE "+   " ".join(condition)+" END ")
    if len(fup) > 0:
        qu = "UPDATE "+state.schema_name+"."+df.table_name+" SET "+",".join(fup)
        cursor.execute(qu)
        conn.commit()
    return

  
def clean_meta_file(infile,outdir,s):       ## update or remove ***
    ''' create in outdir a metadata file based on infile, with all unnecessaries stripped, for the given state'''
    if s.abbreviation == 'NC':
        return("hello") # need to code this *** 
    else:
        return("clean_meta_file: error, state not recognized")
        sys.exit()
