#!/bin/bash

mkdir static/uploads
sqlite3 samplereg.db < schema.sql
./makeids.py 100
