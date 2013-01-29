#!/bin/bash

mkdir uploads
cd static 
ln -s ../uploads
cd ..
sqlite3 samplereg.db < schema.sql
./makeids.py 100
