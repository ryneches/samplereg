#!/usr/bin/env python
import sys
import random

ids = []


for i in range( int(sys.argv[1]) ) :
        
    a = []
    for j in range(7) :
        a.append(random.choice( 'abcdefghijklmnopqrstuvwxyz0123456789' ))
    id = ''.join(a)
    if not ids.__contains__( id ) :
        ids.append(id)

open( 'ids.txt', 'w' ).write( '\n'.join(ids) )
