#!usr/bin/python3

########## next four lines are necessary to install numpy and pandas packages for some reason...
import os
os.system("pip install --upgrade pip")
os.system("pip install pandas")
os.system("pip install numpy")

import numpy as np
import pandas as pd
from flask import Flask
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT # allows db creation, deletion
import re
import states_and_files as sf
from pathlib import Path
import sys
# do we need numpy? If not, remove from requirements

from datetime import datetime

import query_create as q
import clean as cl

## define some basics
def path_to_file(path_to_dir,filename):
    if path_to_dir[-1] == '/':
        out = path_to_dir
    else:
        out = path_to_dir+'/'
    return(out+filename)

def establish_connection(db_name='postgres'):
    host_name = 'db'
    user_name = 'postgres'
    password = 'notverysecure'

    # the connect() function returns a new instance of connection
    conn = psycopg2.connect(host = host_name, user = user_name, password = password, database = db_name)
    return conn

def create_cursor(connection):
    # create a new cursor with the connection object.
    cur = connection.cursor()
    return cur

def check_args(s,f,t):
    if not isinstance(s,sf.State):
        return('Error: '+s+' is not a known state.')
        sys.exit()
    mypath=Path(f)
    if not mypath.is_file():
        return('Error: File '+f+' does not exist.')
        sys.exit()
    # *** check t for whitespace
    return (s,f,t)

def create_db(s):
    # connect and create db for the state
    conn = establish_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    query = 'DROP DATABASE IF EXISTS '+s.db_name
    cur.execute(query)

    
    query = 'CREATE DATABASE '+s.db_name
    cur.execute(query)
    if cur:
        cur.close()
    if conn:
        conn.close()



app = Flask(__name__)

@app.route('/build')
def build():
# initialize report for logging
    report=[]
#    tables = [['results_pct','utf8'],['absentee','utf16']] # varies by state *** name and encoding of metadata file
        # note: 'absentee' needs better data cleaning
#    fmeta = {'results_pct':'layout_results_pct.txt','absentee':'sfs_by_hand_layout_absentee.txt'}  # name of metadata file; varies by state ***
#    fdata = {'results_pct':'results_pct_20181106.txt','absentee':'absentee_20181106.csv'} # name of data file, varies by state and election ***
# set global log file
    now=datetime.now()
    now_str=now.strftime('%Y%b%d%H%M')
    logfilepath = 'local_logs/hello'+now_str+'.log'
    with open(logfilepath,'a') as sys.stdout:

    # instantiate state of NC
        s = sf.create_state('NC')
    # instantiate the NC datafiles
        datafiles = [sf.create_datafile('NC','results_pct_20181106.txt'), sf.create_datafile('NC','absentee_20181106.csv')]

    # create the db for the state
        create_db(s)

    # connect to the state db
        report.append('Connect to database '+s.db_name)
        conn = establish_connection(s.db_name)
        cur = conn.cursor()
        
        for d in datafiles:
            t = d.table_name   # name of table
            e = d.metafile_encoding
            fpath = 'local_data/NC/meta/'+d.metafile_name   # this path is outside the docker container.
            check_args(s,fpath,t)   # checking s is redundant
        
        # clean the metadata file
            fpath = cl.extract_first_col_defs(fpath,'local_data/tmp/',e)

        # create table and commit
            [drop_query,create_query] = q.create_table(t,fpath,s,e)
            cur.execute(drop_query)
            report.append(drop_query)
            cur.execute(create_query)
            report.append(create_query)
            conn.commit()

    # correct any errors due to foibles of particular state and commit
        for query in s.correction_query_list:
            cur.execute(query)
            report.append(query)
            conn.commit()

    # load data into tables
        for d in datafiles:
            q.load_data(conn,cur,s,d)
            report.append('Data from file '+d.file_name+' loaded into table '+d.table_name)
    
    # close connection
        if cur:
            cur.close()
        if conn:
            conn.close()
        return("<p>"+"</p><p>  ".join(report))


@app.route('/analyze')
def analyze():
    report=[""]
# instantiate state of NC
    s = sf.create_state('NC')
    conn = establish_connection(s.db_name)
    cur = conn.cursor()
    
# hard code table for now *** need to modify build() to track source file, separate build() and load()
    table_name = 'results_pct'
    contest_field = 'contest_name'
    county_field = 'county'
    vote_field = 'absentee_by_mail'
    party_field = 'choice_party'
    tolerance = 2  ## number of standard deviations from the mean that we're calling outliers
    
    
    q_abs = "SELECT "+contest_field+", "+county_field+","+party_field+", sum("+vote_field+") FROM "+table_name+"  GROUP BY "+contest_field+", "+county_field+","+party_field+" ORDER BY "+contest_field+", "+county_field+","+party_field
    cur.execute(q_abs)
    votes = pd.DataFrame(cur.fetchall(),columns=['contest','county','party','votes'])
    contests = votes['contest'].unique().tolist()     # list of contests

# loop through contests

    for c in contests:
    # for given contest_name, calculate DEM votes and total votes on absentee ballots by county
        if c:
            report.append(c)
            c_votes=votes[votes.contest==c]
            if 'DEM' in c_votes['party'].values:
                table = pd.pivot_table(c_votes, values='votes', index=['county'], columns=['party'], aggfunc=np.sum).fillna(0)
                table['total']= table.DEM + table.REP #  + table.CST + table.LIB + table.GRE *** how to sum NaN? How to automate this list?
                table['pct_DEM'] = table.DEM/table.total
            # find outliers
                mean = table['pct_DEM'].mean()
                std = table['pct_DEM'].std()
                outliers = table[np.absolute(table.pct_DEM-mean)> tolerance*std]
                # report.append(str(table['pct_DEM']))
                if outliers.empty:
                    report.append("No outliers more than "+str(tolerance)+" standard deviations from mean")
                else:
                    report.append("Outliers are:"+str(outliers))
            else:
                report.append("No DEM votes in contest "+c)

    # look for outlier in DEM percentage
    
    if cur:
        cur.close()
    if conn:
        conn.close()


    
    return("<p>"+"</p><p>  ".join(report))

