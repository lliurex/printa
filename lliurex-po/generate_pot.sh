#!/bin/bash

FILE_POT="printa/printa.pot"
EXT=".ui"
if [ ! -f $FILE_POT ]; then
	touch $FILE_POT
else
	rm $FILE_POT
	touch $FILE_POT
fi

xgettext --join-existing ../printa-users-manager/usr/share/printa-users-manager/rsrc/printa-manager.ui -o $FILE_POT
echo "Finished, you can review $FILE_POT"
