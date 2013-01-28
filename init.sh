#!/bin/bash

mkdir uploads
sqlite3 samplereg.db < schema.sql
./makeids.py 100
