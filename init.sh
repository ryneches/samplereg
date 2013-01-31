#!/bin/bash

sqlite3 samplereg.db < schema.sql
./makeids.py 100
