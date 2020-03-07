#!/bin/bash

rsync -Lrzva --exclude sync.sh --exclude orig --exclude .DS_Store . smanmi@figur.li:www/

