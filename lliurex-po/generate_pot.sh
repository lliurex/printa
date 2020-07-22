#!/bin/bash

FILE_POT="printa/printa.pot"
INDEX_PO="printa/es_ES.po"
INDEX_VAL_PO="printa/ca@valencia.po"
EXT=".ui"
if [ ! -f $FILE_POT ]; then
	touch $FILE_POT
else
	rm $FILE_POT
	touch $FILE_POT
fi

xgettext --join-existing ../printa-users-manager/usr/share/printa-users-manager/rsrc/printa-manager.ui -o $FILE_POT
xgettext --language=Python --join-existing ../printa-users-manager/usr/share/printa-users-manager/printa-users-manager -o $FILE_POT
xgettext --language=Python --join-existing ../printa-users-manager/usr/share/printa-users-manager/N4dLogin.py -o $FILE_POT
xgettext --join-existing ../printa-printer-config/usr/share/printa-printer-config/rsrc/printa-printer-config-gui.ui -o $FILE_POT
xgettext --language=Python --join-existing ../printa-printer-config/usr/sbin/printa-printer-config-gui -o $FILE_POT
echo "Finished, you can review $FILE_POT"
while true; do
	read -p "Do you want generate merge now?" yn
	case $yn in
        [Yy]* ) msgmerge -U $INDEX_PO $FILE_POT; echo "Updated Spanish file: $INDEX_PO"; msgmerge -U $INDEX_VAL_PO $FILE_POT; echo "Updated Valencia file: $INDEX_VAL_PO"; break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

