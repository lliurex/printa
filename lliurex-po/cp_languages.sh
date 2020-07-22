#!/bin/bash
DIR="printa/"
SP_ORIG="es_ES.po"
VAL_ORIG="ca@valencia.po"
SP_FILES=("es_ES.UTF-8.po"  "es.po")
VAL_FILES=("ca_ES.utf8@valencia"  "ca_ES.UTF-8@valencia.po"  "ca_ES@valencia.po")
for i in ${SP_FILES[*]}; do 
	cp $DIR$SP_ORIG $DIR$i
	echo "$i updated"
done


for i in ${VAL_FILES[*]}; do 
	cp $DIR$VAL_ORIG $DIR$i
	echo "$i updated"
done