#!/bin/bash

rsync -rzva --exclude sync.sh --exclude orig --exclude .DS_Store . smanmi@figur.li:www/

